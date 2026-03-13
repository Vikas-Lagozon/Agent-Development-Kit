# research.py
# ─────────────────────────────────────────────────────────────
# Research Agent Module
#
# Flow:
#   1. Get topic from user
#   2. Call get_current_datetime() in Python (mandatory, not via LLM tool)
#   3. Google Search is ALWAYS performed (mandatory for every topic)
#   4. Generate 2–8 search queries via LLM — output captured directly from
#      events (NOT via output_key / SequentialAgent — unreliable in this ADK version)
#   5. Run all queries in parallel → collect results into a Python list
#   6. Synthesiser combines search results list + own knowledge → markdown report
# ─────────────────────────────────────────────────────────────

import os
import logging
import datetime
import re
from pathlib import Path
from typing import AsyncGenerator, ClassVar, List

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.google_search_tool import google_search
from google.genai import types

from .config import config

# ─────────────────────────────────────────────────────────────
# LOGGING
# Direct handlers on named logger — works under both adk web and chatbot.py.
# basicConfig is a no-op under adk web (uvicorn pre-configures root logger).
# ─────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "log"
_LOG_DIR.mkdir(exist_ok=True)

_log_filename = datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S") + ".log"
_log_filepath = _LOG_DIR / _log_filename

_log_formatter = logging.Formatter(
    "%(asctime)s  [%(module)s]  %(levelname)-8s  %(name)s  %(message)s"
)

logger = logging.getLogger("research_agent")
logger.setLevel(logging.DEBUG)

_file_handler = logging.FileHandler(_log_filepath, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_log_formatter)
logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)
_console_handler.setFormatter(_log_formatter)
logger.addHandler(_console_handler)

logger.propagate = False
logger.info(f"Research Agent initialised. Log → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
RESEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

MIN_QUERIES = 2
MAX_QUERIES = 8

# ─────────────────────────────────────────────────────────────
# SESSION STATE KEYS
# ─────────────────────────────────────────────────────────────
KEY_ORIGINAL_QUERY   = "research:original_query"
KEY_CURRENT_DATETIME = "research:current_datetime"
KEY_FINAL_REPORT     = "research:final_report"


# ─────────────────────────────────────────────────────────────
# TOOL: get_current_datetime
# Called directly in Python — NOT passed to any LlmAgent as a tool.
# Exported so root_agent can use it for date/time queries.
# ─────────────────────────────────────────────────────────────
def get_current_datetime() -> str:
    """Returns the current date, time, and day of the week."""
    now = datetime.datetime.now()
    result = now.strftime("%A, %B %d, %Y, %I:%M %p")
    logger.debug(f"get_current_datetime called → {result}")
    return result


# ─────────────────────────────────────────────────────────────
# SEARCH WORKER
# ─────────────────────────────────────────────────────────────
class SearchWorker(BaseAgent):
    """Runs a single google_search query and saves the result to state."""

    worker_index: int
    query: str

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, *, name: str, worker_index: int, query: str):
        super().__init__(name=name, worker_index=worker_index, query=query)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Searching → '{self.query}'")

        inner = LlmAgent(
            name=f"inner_search_{self.worker_index}",
            model=RESEARCH_MODEL,
            instruction=f"""
Use the google_search tool to search for: "{self.query}"

Return a detailed, factual summary of the most relevant and recent results.
Include key facts, dates, figures, and source names where available.
Output ONLY the factual summary — no preamble, no opinions.
""",
            tools=[google_search],
        )

        result_text = ""
        async for event in inner.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result_text += part.text

        logger.info(f"[{self.name}] Result length: {len(result_text)} chars")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=result_text or "No result.")],
            ),
            actions=EventActions(
                state_delta={f"research:result:{self.worker_index}": result_text}
            ),
        )


logger.debug("SearchWorker defined.")


# ─────────────────────────────────────────────────────────────
# PUBLIC WRAPPER — ResearchAgent (BaseAgent)
#
# All orchestration is done directly in Python here — no SequentialAgent.
# Root cause of the previous empty-query bug: output_key on a LlmAgent
# inside a SequentialAgent was not reliably flushing to ctx.session.state
# before the next agent ran in this ADK version. Fix: run the query builder
# directly with run_async() and capture its text output from the event stream.
# ─────────────────────────────────────────────────────────────
class ResearchAgent(BaseAgent):
    """
    Public-facing research agent.
    Google Search is ALWAYS performed (mandatory for every topic).
    All orchestration in Python — no SequentialAgent dependency.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="research_agent",
            description=(
                "Performs deep research on any topic using mandatory parallel web "
                "searches and own knowledge base, returning a structured markdown report."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info("[ResearchAgent] Pipeline started.")

        # ── STEP 1: Extract original query
        original_query = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    original_query += part.text

        if not original_query:
            original_query = ctx.session.state.get(KEY_ORIGINAL_QUERY, "")
            if original_query:
                logger.info("[ResearchAgent] original_query recovered from state.")

        if not original_query:
            logger.warning("[ResearchAgent] Could not extract original_query.")
        else:
            logger.info(f"[ResearchAgent] original_query='{original_query}'")

        # ── STEP 2: Get current datetime in Python
        current_datetime = get_current_datetime()
        logger.info(f"[ResearchAgent] current_datetime='{current_datetime}'")

        ctx.session.state[KEY_ORIGINAL_QUERY]   = original_query
        ctx.session.state[KEY_CURRENT_DATETIME] = current_datetime

        # ── STEP 3: Run query builder and capture output directly from event stream
        # We do NOT use output_key or SequentialAgent — we read the LLM text directly
        # from the final event. This is the reliable way to get LLM output in this ADK version.
        current_year = datetime.datetime.now().year
        query_builder = LlmAgent(
            name="query_builder_agent",
            model=RESEARCH_MODEL,
            instruction=f"""
You are a Search Query Planner.

Current date and time: {current_datetime}
User research topic: {original_query}

Generate between {MIN_QUERIES} and {MAX_QUERIES} highly specific and diverse Google
search queries that together provide comprehensive coverage of the topic.

Rules:
- Each query must target a completely different angle or sub-topic.
- Always include the current year ({current_year}) in at least some queries.
- Cover: latest news, key facts, expert analysis, statistics, comparisons.

Output ONLY a numbered list — nothing else, no explanation, no preamble:
1. first search query
2. second search query
3. third search query
""",
        )

        raw_query_text = ""
        async for event in query_builder.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        raw_query_text += part.text

        logger.debug(f"[ResearchAgent] raw_query_text:\n{raw_query_text}")

        # ── STEP 4: Parse numbered list into Python list of query strings
        queries: List[str] = []
        for line in raw_query_text.strip().splitlines():
            line = line.strip()
            match = re.match(r"^\d+[\.\)]\s+(.+)$", line)
            if match:
                q = match.group(1).strip()
                if q:
                    queries.append(q)

        logger.info(f"[ResearchAgent] Parsed {len(queries)} queries.")

        # Pad if under minimum
        if len(queries) < MIN_QUERIES:
            logger.warning(f"[ResearchAgent] Padding queries from {len(queries)} to {MIN_QUERIES}.")
            fallbacks = [
                f"{original_query} overview {current_year}",
                f"{original_query} latest research {current_year}",
                f"{original_query} key findings {current_year}",
            ]
            while len(queries) < MIN_QUERIES:
                pad = fallbacks[len(queries) % len(fallbacks)]
                queries.append(pad if pad not in queries else f"{original_query} part {len(queries)+1}")

        queries = queries[:MAX_QUERIES]

        logger.info(f"[ResearchAgent] Final query count: {len(queries)}")
        for i, q in enumerate(queries):
            logger.info(f"  [{i}] {q}")

        # ── STEP 5: Run all search workers in parallel and collect results
        # directly from the event stream — NOT from state after the fact.
        # ParallelAgent worker state_delta writes are not guaranteed to be
        # flushed to ctx.session.state before the async-for loop ends, which
        # caused "Collected 0 non-empty results" despite workers returning data.
        workers = [
            SearchWorker(name=f"search_worker_{i}", worker_index=i, query=q)
            for i, q in enumerate(queries)
        ]

        parallel = ParallelAgent(name="parallel_search_agent", sub_agents=workers)

        # Map worker name → query so we can label results correctly
        worker_query_map = {f"search_worker_{i}": q for i, q in enumerate(queries)}
        worker_results: dict = {}  # worker_name → captured text

        logger.info(f"[ResearchAgent] Running {len(workers)} parallel searches.")
        async for event in parallel.run_async(ctx):
            if (
                event.author in worker_query_map
                and event.is_final_response()
                and event.content
                and event.content.parts
            ):
                text = "".join(
                    part.text for part in event.content.parts
                    if getattr(part, "text", None)
                ).strip()
                if text and text != "No result.":
                    worker_results[event.author] = text
                    logger.info(
                        f"[ResearchAgent] Captured result from {event.author}: {len(text)} chars"
                    )

        # Build ordered results list
        results_list: List[str] = []
        for i, q in enumerate(queries):
            text = worker_results.get(f"search_worker_{i}", "")
            if text:
                results_list.append(f"[Search {i+1}: {q}]\n{text}")

        logger.info(f"[ResearchAgent] Collected {len(results_list)} non-empty results.")

        # ── STEP 7: Build synthesiser with results embedded directly in the prompt
        search_block = "\n\n".join(results_list) if results_list else "No search results available."

        synthesiser = LlmAgent(
            name="synthesiser_agent",
            model=RESEARCH_MODEL,
            instruction=f"""
You are a Senior Research Analyst.

Current date and time: {current_datetime}
User research query: {original_query}

--- GOOGLE SEARCH RESULTS ---
{search_block}
--- END OF SEARCH RESULTS ---

Produce a comprehensive markdown research report combining the search results
above with your own knowledge base on this topic.

## Executive Summary
(2–3 sentence overview combining search findings and your knowledge)

## Key Findings from Web Search
(Bullet points — facts, figures, dates from the search results above only.
 If no search results, write: "No web search results available.")

## Analysis & Knowledge Base Insights
(Your own expert knowledge and analysis. Do NOT repeat search result content.)

## Detailed Analysis
(Deep dive combining both sources — cover all major angles)

## Notable Facts & Data Points
(Specific figures, statistics, dates — label source as "Web" or "Knowledge Base")

## Conclusion
(Final synthesis of all evidence and insights)

RULES:
- Write in clear, professional markdown.
- Do not fabricate statistics — say "approximate" or "estimated" if unsure.
- Report length: 600–1500 words.
""",
            output_key=KEY_FINAL_REPORT,
        )

        final_report = ""
        async for event in synthesiser.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_report += part.text

        if not final_report:
            final_report = ctx.session.state.get(KEY_FINAL_REPORT, "")
            if final_report:
                logger.info("[ResearchAgent] Report recovered from state.")

        if not final_report:
            final_report = "Research complete. No report was generated."
            logger.warning("[ResearchAgent] Pipeline produced no output.")

        logger.info(f"[ResearchAgent] Pipeline complete. Report length: {len(final_report)} chars.")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=final_report)],
            ),
            actions=EventActions(state_delta={KEY_FINAL_REPORT: final_report}),
        )


# ─────────────────────────────────────────────────────────────
# PUBLIC EXPORTS
# ─────────────────────────────────────────────────────────────
research_agent = ResearchAgent()

__all__ = ["research_agent", "get_current_datetime"]
