# problem_solver.py
# ─────────────────────────────────────────────────────────────
# Problem Solver Agent Module
#
# Pipeline:
#   Problem Statement
#     └─> PSEntryAgent [BaseAgent]   (saves problem to state FIRST before pipeline)
#           └─> ps_analyser_agent   (reads {ps:problem} from state, analyses it,
#                                    generates 2–5 targeted queries → state)
#           └─> PSFanOutAgent [BaseAgent]  (parses analyser JSON, builds
#                                          ParallelAgent of N PSSearchWorkers)
#                 └─> ps_worker_0..N  (each runs google_search → state)
#           └─> ps_root_cause_agent  (reads search results + own KB → state)
#           └─> ps_solution_agent    (reads root causes + results → final report)
#     └─> ProblemSolverAgent [BaseAgent]  (public wrapper — surfaces only final report)
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

_ps_logger = logging.getLogger("problem_solver_agent")

if not _ps_logger.handlers:
    _ps_logger.setLevel(logging.DEBUG)
    _fmt = logging.Formatter(
        "%(asctime)s  [%(module)s]  %(levelname)-8s  %(name)s  %(message)s"
    )
    _fh = logging.FileHandler(_log_filepath, encoding="utf-8")
    _fh.setFormatter(_fmt)
    _ps_logger.addHandler(_fh)
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    _ps_logger.addHandler(_sh)

_ps_logger.info(f"Problem Solver Agent initialised. Log → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
RESEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# ─────────────────────────────────────────────────────────────
# SESSION STATE KEYS  (all prefixed "ps:" to avoid collisions)
# ─────────────────────────────────────────────────────────────
PS_KEY_PROBLEM         = "ps:problem"
PS_KEY_QUERIES_JSON    = "ps:queries_json"
PS_KEY_RESULT_PREFIX   = "ps:result:"
PS_KEY_ROOT_CAUSE      = "ps:root_cause"
PS_KEY_SOLUTION_REPORT = "ps:solution_report"

# ─────────────────────────────────────────────────────────────
# HELPER: robust JSON extractor
# ─────────────────────────────────────────────────────────────
def _ps_extract_json(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


# ─────────────────────────────────────────────────────────────
# STEP 0 — PS ENTRY AGENT  (BaseAgent)
# ─────────────────────────────────────────────────────────────
class PSEntryAgent(BaseAgent):
    """
    Reads the user's problem from ctx.user_content and writes it to
    session state under PS_KEY_PROBLEM before the pipeline starts.
    """
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(name="ps_entry_agent")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        problem_text = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    problem_text += part.text

        _ps_logger.info(f"[PSEntryAgent] Captured problem ({len(problem_text)} chars): "
                        f"'{problem_text[:120]}{'...' if len(problem_text) > 120 else ''}'")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Problem captured. Starting analysis...")],
            ),
            actions=EventActions(state_delta={PS_KEY_PROBLEM: problem_text}),
        )


# ─────────────────────────────────────────────────────────────
# STEP 1 — PS ANALYSER AGENT
# ─────────────────────────────────────────────────────────────
ps_analyser_agent = LlmAgent(
    name="ps_analyser_agent",
    model=RESEARCH_MODEL,
    description="Analyses a programming/technical problem and generates targeted search queries.",
    instruction="""
You are an expert Technical Problem Analyst with deep knowledge in software engineering,
programming languages, system design, DevOps, and computer science fundamentals.

The problem statement to analyse is:
{ps:problem}

Your job has TWO parts:

PART A — Analyse the problem using your own knowledge:
1. Identify the problem type (e.g. runtime error, configuration issue, logic bug,
   dependency conflict, network issue, OS-level error, etc.)
2. Identify the technology stack involved (language, framework, library, OS, etc.)
3. List the most likely possible root causes based on your knowledge.
4. Note any patterns, keywords, or error codes that are significant.

PART B — Generate 2 to 5 highly targeted Google search queries:
- Queries must cover BOTH: (a) root cause investigation AND (b) solution/fix finding.
- Queries must be specific — include error codes, library names, version hints if present.
- Do NOT generate more than 5 queries and not fewer than 2.
- Mix query angles: "cause of X", "fix for X", "X solution stackoverflow", etc.

Output ONLY the following JSON object — no explanation, no markdown fences:
{
  "problem_type": "<type of problem>",
  "technology_stack": ["<tech1>", "<tech2>", "..."],
  "initial_analysis": "<your own knowledge-based understanding of the problem>",
  "possible_causes": ["<cause1>", "<cause2>", "..."],
  "queries": [
    "query 1",
    "query 2",
    "...",
    "query N"
  ]
}
""",
    output_key=PS_KEY_QUERIES_JSON,
)
_ps_logger.debug("ps_analyser_agent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 2 — PS FAN-OUT AGENT  (BaseAgent)
# Parses analyser JSON, writes metadata to state, launches N
# parallel PSSearchWorkers.
# ─────────────────────────────────────────────────────────────

class PSSearchWorker(BaseAgent):
    """Runs a single google_search query and saves result to state."""

    worker_index: int
    query_key: str

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, *, name: str, worker_index: int, query_key: str):
        super().__init__(name=name, worker_index=worker_index, query_key=query_key)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        query = ctx.session.state.get(self.query_key, "")
        _ps_logger.info(f"[{self.name}] Searching → '{query}'")

        if not query:
            _ps_logger.warning(f"[{self.name}] Empty query — skipping.")
            yield Event(
                author=self.name,
                content=types.Content(role="model", parts=[types.Part(text="")]),
                actions=EventActions(
                    state_delta={PS_KEY_RESULT_PREFIX + str(self.worker_index): ""}
                ),
            )
            return

        inner = LlmAgent(
            name=f"ps_inner_search_{self.worker_index}",
            model=RESEARCH_MODEL,
            instruction=f"""
You are a technical research assistant.
Use the google_search tool to search for: "{query}"

Focus on:
- Official documentation, GitHub issues, Stack Overflow answers
- Error explanations and root causes
- Step-by-step fixes and verified solutions
- Version-specific fixes if relevant

Return a detailed, structured summary of findings.
Include source names, code snippets if found, and solution steps.
Output ONLY the summary — no preamble.
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

        _ps_logger.info(f"[{self.name}] Result length: {len(result_text)} chars")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=result_text)],
            ),
            actions=EventActions(
                state_delta={PS_KEY_RESULT_PREFIX + str(self.worker_index): result_text}
            ),
        )


class PSFanOutAgent(BaseAgent):
    """Parses analyser JSON, writes metadata+queries to state, runs parallel search."""

    MAX_WORKERS: ClassVar[int] = 5

    def __init__(self):
        super().__init__(name="ps_fan_out_agent")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:

        raw_json = ctx.session.state.get(PS_KEY_QUERIES_JSON, "{}")
        _ps_logger.debug(f"[PSFanOutAgent] raw analyser output: {raw_json[:300]}")

        clean = _ps_extract_json(raw_json)
        _ps_logger.debug(f"[PSFanOutAgent] cleaned JSON: {clean[:300]}")

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            _ps_logger.error(f"[PSFanOutAgent] JSON parse error: {e} | raw: {raw_json}")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Failed to parse analyser output.")],
                ),
            )
            return

        queries: List[str] = parsed.get("queries", [])
        queries = queries[: self.MAX_WORKERS]
        problem_type     = parsed.get("problem_type", "unknown")
        tech_stack       = parsed.get("technology_stack", [])
        initial_analysis = parsed.get("initial_analysis", "")
        possible_causes  = parsed.get("possible_causes", [])

        _ps_logger.info(
            f"[PSFanOutAgent] problem_type='{problem_type}' | "
            f"tech_stack={tech_stack} | num_queries={len(queries)}"
        )
        _ps_logger.info(f"[PSFanOutAgent] possible_causes={possible_causes}")

        if not queries:
            _ps_logger.warning("[PSFanOutAgent] No search queries generated.")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="No search queries were generated.")],
                ),
            )
            return

        # Write all metadata + query keys to state in one delta
        state_delta: dict = {
            "ps:problem_type":    problem_type,
            "ps:tech_stack":      json.dumps(tech_stack),
            "ps:initial_analysis": initial_analysis,
            "ps:possible_causes": json.dumps(possible_causes),
        }
        for i, q in enumerate(queries):
            state_delta[f"ps:query:{i}"] = q

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Launching {len(queries)} parallel searches...")],
            ),
            actions=EventActions(state_delta=state_delta),
        )

        # Build fresh PSSearchWorker instances (one-parent-per-agent rule)
        workers = [
            PSSearchWorker(
                name=f"ps_search_worker_{i}",
                worker_index=i,
                query_key=f"ps:query:{i}",
            )
            for i in range(len(queries))
        ]

        parallel = ParallelAgent(
            name="ps_parallel_search_agent",
            sub_agents=workers,
        )

        _ps_logger.info(f"[PSFanOutAgent] Running ParallelAgent with {len(workers)} workers.")
        async for event in parallel.run_async(ctx):
            yield event

        _ps_logger.info("[PSFanOutAgent] All parallel workers completed.")


_ps_logger.debug("PSFanOutAgent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 3 — PS ROOT CAUSE AGENT
# ─────────────────────────────────────────────────────────────
ps_root_cause_agent = LlmAgent(
    name="ps_root_cause_agent",
    model=RESEARCH_MODEL,
    description="Identifies root causes of the problem from search results and own knowledge.",
    instruction=f"""
You are a Senior Software Engineer and Debugging Expert.

You have the following information in session state:

Problem Statement: {{ps:problem}}
Problem Type: {{ps:problem_type}}
Technology Stack: {{ps:tech_stack}}
Initial Analysis (from knowledge base): {{ps:initial_analysis}}
Possible Causes (from knowledge base): {{ps:possible_causes}}

Search results from web research:
Result 0: {{ps:result:0}}
Result 1: {{ps:result:1}}
Result 2: {{ps:result:2}}
Result 3: {{ps:result:3}}
Result 4: {{ps:result:4}}

Your task — produce a thorough root cause analysis:
1. Combine web search findings with your own technical knowledge.
2. Identify the PRIMARY root cause (most likely cause).
3. Identify SECONDARY possible causes (other contributing factors).
4. Explain WHY each cause produces the observed problem.
5. Note any patterns, commonalities, or key indicators from the search results.

Output ONLY the following JSON — no markdown fences, no preamble:
{{
  "primary_root_cause": "<the most likely root cause with explanation>",
  "secondary_causes": [
    "<secondary cause 1>",
    "<secondary cause 2>",
    "..."
  ],
  "key_indicators": ["<indicator1>", "<indicator2>", "..."],
  "affected_components": ["<component1>", "<component2>", "..."],
  "severity": "low | medium | high | critical",
  "summary": "<2-3 sentence plain English explanation of why this problem occurs>"
}}
""",
    output_key=PS_KEY_ROOT_CAUSE,
)
_ps_logger.debug("ps_root_cause_agent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 4 — PS SOLUTION AGENT
# BUG FIX 3 (continued): Correct {{ }} brace escaping.
# ─────────────────────────────────────────────────────────────
ps_solution_agent = LlmAgent(
    name="ps_solution_agent",
    model=RESEARCH_MODEL,
    description="Generates a complete step-by-step solution for the identified problem.",
    instruction=f"""
You are a Senior Software Engineer and Solutions Architect.

You have the following information in session state:

Problem Statement: {{ps:problem}}
Problem Type: {{ps:problem_type}}
Technology Stack: {{ps:tech_stack}}
Root Cause Analysis: {{ps:root_cause}}

Search results from web research:
Result 0: {{ps:result:0}}
Result 1: {{ps:result:1}}
Result 2: {{ps:result:2}}
Result 3: {{ps:result:3}}
Result 4: {{ps:result:4}}

Your task — generate a complete, production-ready solution report in markdown:

## Problem Summary
(Restate the problem clearly in 2-3 sentences)

## Root Cause
(Explain the identified root cause in plain language)

## Solution

### Primary Fix
(The main recommended solution with step-by-step instructions)
- Include exact commands, code snippets, configuration changes as needed
- Be specific — use actual values from the problem statement where possible

### Alternative Solutions
(1-3 other approaches if the primary fix does not work)

## Prevention
(How to avoid this problem in the future — best practices, checks, etc.)

## Verification
(How to confirm the fix worked — test commands, expected outputs, etc.)

## References
(Mention the sources / search queries that informed this solution)

Rules:
- Be precise and actionable — every step must be executable.
- Include code blocks where relevant using triple backticks.
- Do NOT hallucinate solutions not supported by the research or your knowledge.
- If multiple solutions exist, rank them by reliability.
""",
    output_key=PS_KEY_SOLUTION_REPORT,
)
_ps_logger.debug("ps_solution_agent defined.")


# ─────────────────────────────────────────────────────────────
# PIPELINE ASSEMBLY
# PSEntryAgent runs FIRST to write the problem to state,
# then the rest of the pipeline reads it via {ps:problem}.
# ─────────────────────────────────────────────────────────────
_ps_entry_agent   = PSEntryAgent()
_ps_fan_out_agent = PSFanOutAgent()

_ps_pipeline = SequentialAgent(
    name="ps_pipeline",
    description="Internal problem solver pipeline: capture → analyse → search → root cause → solution.",
    sub_agents=[
        _ps_entry_agent,       # Step 0: saves problem to state
        ps_analyser_agent,     # Step 1: reads {ps:problem}, generates queries
        _ps_fan_out_agent,     # Step 2: parallel search
        ps_root_cause_agent,   # Step 3: root cause analysis
        ps_solution_agent,     # Step 4: final solution report
    ],
)

_ps_logger.info("Problem Solver pipeline assembled.")


# ─────────────────────────────────────────────────────────────
# PUBLIC WRAPPER — ProblemSolverAgent (BaseAgent)
# ─────────────────────────────────────────────────────────────
class ProblemSolverAgent(BaseAgent):
    """
    Analyses programming errors, stack traces, bugs, and technical issues.
    Identifies root causes and provides step-by-step solutions.
    Use this agent for: error messages, exceptions, crashes, bugs,
    configuration problems, dependency issues, and any technical problem
    that requires debugging or a fix.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="problem_solver_agent",
            description=(
                "Analyses programming errors, stack traces, exceptions, bugs, crashes, "
                "configuration issues, and technical problems. Identifies root causes "
                "using Google Search and knowledge base, then provides step-by-step "
                "solutions. Use for any error message, bug report, or technical issue "
                "that needs debugging and fixing."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        _ps_logger.info("[ProblemSolverAgent] Pipeline started.")

        final_solution = ""

        async for event in _ps_pipeline.run_async(ctx):
            if (
                event.author == "ps_solution_agent"
                and event.is_final_response()
                and event.content
                and event.content.parts
            ):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_solution += part.text

        # Fallback — read from state
        if not final_solution:
            final_solution = ctx.session.state.get(PS_KEY_SOLUTION_REPORT, "")
            if final_solution:
                _ps_logger.info("[ProblemSolverAgent] Solution recovered from state.")

        if not final_solution:
            final_solution = "Problem analysis complete. No solution report was generated."
            _ps_logger.warning("[ProblemSolverAgent] Pipeline produced no output.")

        _ps_logger.info(
            f"[ProblemSolverAgent] Pipeline complete. "
            f"Solution length: {len(final_solution)} chars."
        )

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=final_solution)],
            ),
            actions=EventActions(
                state_delta={PS_KEY_SOLUTION_REPORT: final_solution}
            ),
        )


# ─────────────────────────────────────────────────────────────
# PUBLIC EXPORTS
# ─────────────────────────────────────────────────────────────
problem_solver_agent = ProblemSolverAgent()

__all__ = ["problem_solver_agent"]
