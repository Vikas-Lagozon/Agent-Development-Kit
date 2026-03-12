# research.py
# ─────────────────────────────────────────────────────────────
# Research Agent Module
#
# Pipeline:
#   User Query
#     └─> reducer_agent       (calls get_current_datetime, decides if search needed,
#                              generates 3–8 queries → state)
#           └─> QueryFanOutAgent  [BaseAgent]  (saves original query to state,
#                                              dynamically builds ParallelAgent of N workers)
#                 └─> worker_1 .. worker_N    (each searches, saves result_i → state)
#           └─> collector_agent  (reads all results → combined state, NO free hallucination)
#     └─> orchestrator_agent  (reads combined state → writes final report → state)
#     └─> ResearchAgent [BaseAgent] (public wrapper — surfaces only final report)
#
# Changes from previous version:
#   - Query count enforced: MIN=3, MAX=8 (both reducer instruction + QueryFanOutAgent)
#   - Supports ALL research types: technical, non-technical, factual, latest topics
#   - Reducer no longer skips coding/technical questions — those need live search too
#   - Collector no longer adds free "knowledge base insights" — prevents hallucination
#   - Orchestrator has strict grounding rules: cite only what search results contain
#   - Added _validate_and_pad_queries() to enforce min=3 queries always
#   - Added empty combined_results guard before orchestrator runs
# ─────────────────────────────────────────────────────────────

import os
import json
import logging
import datetime
import re
from pathlib import Path
from typing import AsyncGenerator, ClassVar, List

from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.google_search_tool import google_search
from google.genai import types

from config import config

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "log"
_LOG_DIR.mkdir(exist_ok=True)

_log_filename = datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S") + ".log"
_log_filepath = _LOG_DIR / _log_filename

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  [%(module)s]  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(_log_filepath, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("research_agent")
logger.info(f"Research Agent initialised. Log → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
RESEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# ─────────────────────────────────────────────────────────────
# QUERY COUNT CONSTRAINTS
# ─────────────────────────────────────────────────────────────
MIN_QUERIES = 3
MAX_QUERIES = 8

# ─────────────────────────────────────────────────────────────
# SESSION STATE KEYS
# ─────────────────────────────────────────────────────────────
KEY_ORIGINAL_QUERY   = "research:original_query"
KEY_SEARCH_NEEDED    = "research:search_needed"
KEY_QUERIES_JSON     = "research:queries_json"
KEY_RESULT_PREFIX    = "research:result:"
KEY_COMBINED_RESULTS = "research:combined_results"
KEY_FINAL_REPORT     = "research:final_report"

# ─────────────────────────────────────────────────────────────
# CUSTOM TOOL: get_current_datetime
# ─────────────────────────────────────────────────────────────
def get_current_datetime() -> str:
    """Returns the current date, time, and day of the week."""
    now = datetime.datetime.now()
    result = now.strftime("%A, %B %d, %Y, %I:%M %p")
    logger.debug(f"get_current_datetime called → {result}")
    return result


# ─────────────────────────────────────────────────────────────
# HELPER: robust JSON extractor
# ─────────────────────────────────────────────────────────────
def _extract_json(text: str) -> str:
    """
    Strips markdown code fences (```json ... ``` or ``` ... ```)
    and returns clean JSON string.
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


# ─────────────────────────────────────────────────────────────
# HELPER: enforce MIN/MAX query count
# If reducer returns fewer than MIN_QUERIES, pads with broader queries.
# If reducer returns more than MAX_QUERIES, trims to MAX_QUERIES.
# ─────────────────────────────────────────────────────────────
def _validate_and_pad_queries(queries: List[str], original_query: str) -> List[str]:
    """Ensures MIN_QUERIES <= len(queries) <= MAX_QUERIES."""
    queries = queries[:MAX_QUERIES]  # cap at max first

    if len(queries) < MIN_QUERIES:
        logger.warning(
            f"[validate_queries] Only {len(queries)} queries received — "
            f"padding to minimum of {MIN_QUERIES}."
        )
        current_year = datetime.datetime.now().year
        fallback_templates = [
            f"{original_query} overview {current_year}",
            f"{original_query} latest developments {current_year}",
            f"{original_query} detailed explanation and examples",
            f"{original_query} best practices and use cases",
            f"{original_query} comparison and analysis",
        ]
        while len(queries) < MIN_QUERIES:
            pad = fallback_templates[len(queries) % len(fallback_templates)]
            if pad not in queries:
                queries.append(pad)
            else:
                queries.append(f"{original_query} research part {len(queries) + 1}")

    logger.info(
        f"[validate_queries] Final query count: {len(queries)} "
        f"(min={MIN_QUERIES}, max={MAX_QUERIES})"
    )
    return queries


# ─────────────────────────────────────────────────────────────
# STEP 1 — REDUCER AGENT
# Calls get_current_datetime, decides if search is needed,
# generates 3–8 time-anchored search queries → saves to state.
# ─────────────────────────────────────────────────────────────
reducer_agent = LlmAgent(
    name="reducer_agent",
    model=RESEARCH_MODEL,
    description="Decides if web search is needed and generates 3–8 search queries.",
    instruction="""
You are a Research Planner that supports ALL types of research queries:
technical, non-technical, factual, scientific, news, coding, and everything else.

STEP 1 — Get the current date and time:
Call the `get_current_datetime` tool RIGHT NOW before doing anything else.
Use this to anchor all search queries to the most recent and relevant time period.

STEP 2 — Decide whether live Google Search is required:
Web search IS required for ALL of these:
   - Current events, recent news, latest updates
   - Prices, statistics, real-time data
   - Technical topics: programming, frameworks, tools, libraries, APIs, coding
   - Scientific, medical, engineering topics needing current sources
   - How-to guides, tutorials, best practices, implementation guides
   - Facts that could have changed or evolved since training data
   - Any topic where the user wants up-to-date or comprehensive information
   - Research tasks, writing tasks that need accurate current data

Web search is NOT required ONLY for:
   - Pure mathematics (e.g. "what is 2+2", "prove the Pythagorean theorem")
   - Pure logical reasoning with no real-world facts needed

When in doubt — always do the search.

STEP 3 — If search IS required, generate between 3 and 8 highly specific and
diverse search queries. Rules for query generation:
   - MINIMUM 3 queries. MAXIMUM 8 queries. Never fewer than 3, never more than 8.
   - Each query must target a completely different angle or sub-topic of the query.
   - Always include the current year where relevant (e.g. "Python web scraping 2026").
   - For technical topics: cover libraries/tools, implementation steps, code examples.
   - For news/facts: cover latest data, reports, statistics, comparisons.
   - For general research: cover overview, deep-dive, examples, expert opinions.

STEP 4 — Output ONLY the following JSON object and nothing else:
{
  "search_needed": "yes",
  "queries": [
    "query 1",
    "query 2",
    "query 3",
    "...",
    "query N"
  ]
}

If search is NOT required, output:
{
  "search_needed": "no",
  "queries": []
}

CRITICAL: Output raw JSON only. No explanation, no preamble, no markdown fences.
""",
    tools=[get_current_datetime],
    output_key=KEY_QUERIES_JSON,
)
logger.debug("reducer_agent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 2a — SEARCH WORKER (single query)
# ─────────────────────────────────────────────────────────────
class SearchWorker(BaseAgent):
    """Runs a single google_search query and saves the result to state."""

    worker_index: int
    query_key: str

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, *, name: str, worker_index: int, query_key: str):
        super().__init__(name=name, worker_index=worker_index, query_key=query_key)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        query = ctx.session.state.get(self.query_key, "")
        logger.info(f"[{self.name}] Searching → '{query}'")

        if not query:
            logger.warning(f"[{self.name}] Empty query — skipping.")
            yield Event(
                author=self.name,
                content=types.Content(role="model", parts=[types.Part(text="")]),
                actions=EventActions(
                    state_delta={KEY_RESULT_PREFIX + str(self.worker_index): ""}
                ),
            )
            return

        inner = LlmAgent(
            name=f"inner_search_{self.worker_index}",
            model=RESEARCH_MODEL,
            instruction=f"""
Use the google_search tool to search for: "{query}"

Return a detailed, factual summary of the most relevant and recent results.
Include key facts, dates, figures, and source names where available.
Focus strictly on what the search results contain — do NOT add information from memory.
Output ONLY the factual summary — no preamble, no opinions.
""",
            tools=[google_search],
        )

        result_text = ""
        async for event in inner.run_async(ctx):
            if (
                event.is_final_response()
                and event.content
                and event.content.parts
            ):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result_text += part.text

        logger.info(f"[{self.name}] Result length: {len(result_text)} chars")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=result_text)],
            ),
            actions=EventActions(
                state_delta={KEY_RESULT_PREFIX + str(self.worker_index): result_text}
            ),
        )


# ─────────────────────────────────────────────────────────────
# STEP 2b — QUERY FAN-OUT AGENT  (Custom BaseAgent)
# Enforces MIN=3 / MAX=8 queries via _validate_and_pad_queries().
# Saves original query + all query keys to state before parallel run.
# ─────────────────────────────────────────────────────────────
class QueryFanOutAgent(BaseAgent):
    """
    Reads queries_json from state, validates query count (min=3, max=8),
    saves original query to state, dynamically builds a ParallelAgent of
    N SearchWorkers and runs them.
    """

    MAX_WORKERS: ClassVar[int] = MAX_QUERIES  # 8

    def __init__(self):
        super().__init__(name="query_fan_out_agent")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:

        # Save original user query to state
        original_query = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    original_query += part.text
        logger.debug(f"[QueryFanOutAgent] original_query='{original_query}'")

        raw_json = ctx.session.state.get(KEY_QUERIES_JSON, "{}")
        logger.debug(f"[QueryFanOutAgent] raw reducer output: {raw_json}")

        # Robust fence stripping
        clean = _extract_json(raw_json)
        logger.debug(f"[QueryFanOutAgent] cleaned JSON: {clean[:300]}")

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(f"[QueryFanOutAgent] JSON parse error: {e} | raw: {raw_json}")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Failed to parse reducer output.")],
                ),
            )
            return

        search_needed = parsed.get("search_needed", "no").lower()
        queries: List[str] = parsed.get("queries", [])

        logger.info(
            f"[QueryFanOutAgent] search_needed={search_needed}, "
            f"raw num_queries={len(queries)}"
        )

        if search_needed != "yes" or not queries:
            logger.info("[QueryFanOutAgent] No search required — skipping parallel run.")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="No web search required.")],
                ),
                actions=EventActions(state_delta={
                    KEY_SEARCH_NEEDED: "no",
                    KEY_ORIGINAL_QUERY: original_query,
                }),
            )
            return

        # Enforce MIN=3 / MAX=8
        queries = _validate_and_pad_queries(queries, original_query)

        # Write all query keys + original query to state atomically
        query_state: dict = {
            KEY_SEARCH_NEEDED: "yes",
            KEY_ORIGINAL_QUERY: original_query,
        }
        for i, q in enumerate(queries):
            query_state[f"research:query:{i}"] = q

        logger.info(f"[QueryFanOutAgent] Dispatching {len(queries)} queries:")
        for i, q in enumerate(queries):
            logger.info(f"  [{i}] {q}")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Launching {len(queries)} parallel searches...")],
            ),
            actions=EventActions(state_delta=query_state),
        )

        # Build fresh SearchWorker instances each time (one-parent-per-agent rule)
        workers = [
            SearchWorker(
                name=f"search_worker_{i}",
                worker_index=i,
                query_key=f"research:query:{i}",
            )
            for i in range(len(queries))
        ]

        parallel = ParallelAgent(
            name="parallel_search_agent",
            sub_agents=workers,
        )

        logger.info(f"[QueryFanOutAgent] Running ParallelAgent with {len(workers)} workers.")
        async for event in parallel.run_async(ctx):
            yield event

        logger.info("[QueryFanOutAgent] All parallel workers completed.")


logger.debug("QueryFanOutAgent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 3 — COLLECTOR AGENT
# Organises search results into a structured combined store.
# ANTI-HALLUCINATION: Does NOT inject free "knowledge base insights".
# Strictly organises only what the search results actually contain.
# ─────────────────────────────────────────────────────────────
collector_agent = LlmAgent(
    name="collector_agent",
    model=RESEARCH_MODEL,
    description="Collects and organises all search results into a structured combined research store.",
    instruction=f"""
You are a Research Collector and Organiser.

The session state contains web search results from parallel workers.
Each result is stored under the key pattern: "{KEY_RESULT_PREFIX}<index>"

The search results available in state are:
{{research:result:0}}
{{research:result:1}}
{{research:result:2}}
{{research:result:3}}
{{research:result:4}}
{{research:result:5}}
{{research:result:6}}
{{research:result:7}}

The original user query is: {{research:original_query}}

Your job:
1. Read all non-empty search results above.
2. For each non-empty result, write a concise factual summary of what it found.
3. Extract key facts, figures, dates, and names that appear across the results.
4. Identify themes that recur across multiple results.
5. Note any gaps — topics the user asked about that no result covered.

STRICT ANTI-HALLUCINATION RULES:
- Include ONLY information explicitly stated in the search results above.
- Do NOT add facts, figures, or claims from your own memory or training data.
- Do NOT speculate, infer, or fill gaps with assumed information.
- If a result is empty or irrelevant, write "No result" for that index.
- Attribute each notable fact to its result index (e.g. "result_0: ...").

Output ONLY this JSON structure — no markdown fences, no preamble:
{{
  "original_query": "<the original query>",
  "search_results": [
    {{"query_index": 0, "summary": "Factual summary of result 0, or 'No result' if empty."}},
    {{"query_index": 1, "summary": "Factual summary of result 1, or 'No result' if empty."}},
    {{"query_index": 2, "summary": "Factual summary of result 2, or 'No result' if empty."}},
    {{"query_index": 3, "summary": "..."}},
    {{"query_index": 4, "summary": "..."}},
    {{"query_index": 5, "summary": "..."}},
    {{"query_index": 6, "summary": "..."}},
    {{"query_index": 7, "summary": "..."}}
  ],
  "key_themes": ["theme found in search results only", "..."],
  "notable_facts": ["result_X: specific fact or figure", "result_Y: ...", "..."],
  "data_gaps": ["sub-topic not covered by any result", "..."]
}}
""",
    output_key=KEY_COMBINED_RESULTS,
)
logger.debug("collector_agent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 4 — ORCHESTRATOR AGENT
# Synthesises collected research into a final structured report.
# ANTI-HALLUCINATION: Strict grounding — report only what combined_results contains.
# ─────────────────────────────────────────────────────────────
orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=RESEARCH_MODEL,
    description="Synthesises all collected research into a final structured report.",
    instruction=f"""
You are a Senior Research Analyst and Report Writer.

You have access to a comprehensive research store in the session state:
{{research:combined_results}}

Your task is to generate a detailed, well-structured research report (600–1500 words).

Report structure:
## Executive Summary
(2–3 sentence overview — based ONLY on what the search results found)

## Key Findings
(Bullet-pointed major discoveries from the search results.
 For each finding, note which result index it came from.)

## Detailed Analysis
(Multiple sub-sections covering different aspects found in the search results.
 Only cover aspects that are actually present in the research store.)

## Notable Facts & Data Points
(Specific figures, dates, statistics — ONLY those from the search results.
 Attribute each fact: "According to result_X, ...")

## Gaps & Limitations
(Topics listed in data_gaps that were not covered by the search results.
 Be transparent about what could not be found.)

## Conclusion
(Synthesis of what the search results collectively indicate.
 Do not overstate — reflect only what the evidence supports.)

## Sources Referenced
(List the search queries that were used as research sources)

STRICT ANTI-HALLUCINATION RULES — violating these is a critical failure:
- Use ONLY information present in {{research:combined_results}}.
- Do NOT add facts, claims, figures, or details from your own memory or training.
- If the research store does not contain information about a sub-topic, state:
  "Not found in search results" — never fill the gap with assumed knowledge.
- Every specific claim must reference its result index.
- Never present inferred or assumed information as fact.
- If combined_results is empty or contains no usable data, output exactly:
  "Research collection failed — no results available to report on."
  and stop immediately.
""",
    output_key=KEY_FINAL_REPORT,
)
logger.debug("orchestrator_agent defined.")


# ─────────────────────────────────────────────────────────────
# PIPELINE ASSEMBLY
# ─────────────────────────────────────────────────────────────
fan_out_agent = QueryFanOutAgent()

_research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Internal pipeline: plan → parallel search → collect → report.",
    sub_agents=[
        reducer_agent,
        fan_out_agent,
        collector_agent,
        orchestrator_agent,
    ],
)

logger.info("Research pipeline assembled.")


# ─────────────────────────────────────────────────────────────
# PUBLIC WRAPPER — ResearchAgent (BaseAgent)
# Runs the full pipeline and surfaces only the final report.
# Includes guard: logs warning if combined_results is empty.
# ─────────────────────────────────────────────────────────────
class ResearchAgent(BaseAgent):
    """
    Public-facing research agent.
    Supports all query types: technical, non-technical, factual, news, scientific.
    Runs the full pipeline internally and surfaces only the
    orchestrator's final markdown report as the response.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="research_agent",
            description=(
                "Performs deep research on any topic — technical, non-technical, "
                "factual, news, scientific, coding — using parallel web searches "
                "and returns a structured, grounded report."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info("[ResearchAgent] Pipeline started.")

        final_report = ""

        async for event in _research_pipeline.run_async(ctx):
            # Collect orchestrator final text as it streams
            if (
                event.author == "orchestrator_agent"
                and event.is_final_response()
                and event.content
                and event.content.parts
            ):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_report += part.text

        # Fallback — read from state (orchestrator wrote it via output_key)
        if not final_report:
            final_report = ctx.session.state.get(KEY_FINAL_REPORT, "")
            if final_report:
                logger.info("[ResearchAgent] Report recovered from state.")

        # Guard: log warning if combined_results was empty
        combined = ctx.session.state.get(KEY_COMBINED_RESULTS, "")
        if not combined:
            logger.warning(
                "[ResearchAgent] combined_results is empty — "
                "search may have failed or returned no data."
            )

        if not final_report:
            final_report = "Research complete. No report was generated."
            logger.warning("[ResearchAgent] Pipeline produced no output.")

        logger.info(
            f"[ResearchAgent] Pipeline complete. "
            f"Report length: {len(final_report)} chars."
        )

        # Yield a single clean final event — this is what jarvis_root_agent receives
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=final_report)],
            ),
            actions=EventActions(
                state_delta={KEY_FINAL_REPORT: final_report}
            ),
        )


# ─────────────────────────────────────────────────────────────
# PUBLIC EXPORTS  (used by chatbot.py)
# ─────────────────────────────────────────────────────────────
research_agent = ResearchAgent()

__all__ = ["research_agent", "get_current_datetime"]
