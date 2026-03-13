# problem_solver.py
# ─────────────────────────────────────────────────────────────
# Problem Solver Agent Module
#
# Flow:
#   1. Capture problem from user
#   2. Analyse problem + generate 2–8 search queries via LLM
#      (output captured directly from events — no SequentialAgent/output_key)
#   3. Run all queries in parallel → collect results from event stream
#   4. List out the tree directory of the project if you have the project root folder.
#      Else you can skip this. The project list file tree can help to visualize
#      the project more deeply.
#   5. Read the file if required due to which this error arises. So that you can
#      understand the program also.
#   6. Root cause analysis combining search results + own knowledge
#   7. Generate final markdown solution report
#
# Google Search is ALWAYS mandatory.
# ─────────────────────────────────────────────────────────────

import os
import sys
import logging
import datetime
import re
from pathlib import Path
from typing import AsyncGenerator, List

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.google_search_tool import google_search
from google.adk.tools import FunctionTool
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

_ps_logger = logging.getLogger("problem_solver_agent")
_ps_logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(_log_filepath, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_log_formatter)
_ps_logger.addHandler(_fh)

_sh = logging.StreamHandler()
_sh.setLevel(logging.DEBUG)
_sh.setFormatter(_log_formatter)
_ps_logger.addHandler(_sh)

_ps_logger.propagate = False
_ps_logger.info(f"Problem Solver Agent initialised. Log → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
RESEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

MIN_QUERIES = 2
MAX_QUERIES = 8
PATH_TO_PYTHON = sys.executable

# ─────────────────────────────────────────────────────────────
# SESSION STATE KEYS
# ─────────────────────────────────────────────────────────────
PS_KEY_PROBLEM         = "ps:problem"
PS_KEY_SOLUTION_REPORT = "ps:solution_report"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _sanitize_for_instruction(text: str) -> str:
    """
    Remove all { and } characters from text before embedding it into an
    LlmAgent instruction string.

    ROOT CAUSE: ADK's inject_session_state scans the final assembled
    instruction string with the regex  {+[^{}]*}+  which matches ONE OR
    MORE consecutive { chars followed by content and ONE OR MORE }.
    This means BOTH {var} AND {{var}} are matched — so doubling braces
    does NOT protect against it.  The only safe approach is to ensure
    no { or } characters exist in user-supplied content at all.

    We replace { → ( and } → ) so log lines, stack traces, and JSON
    remain readable in the LLM prompt without triggering the scanner.
    """
    return text.replace("{", "(").replace("}", ")")


# ─────────────────────────────────────────────────────────────
# FILE INSPECTION TOOLS
# ─────────────────────────────────────────────────────────────
IGNORED_DIRS = {
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".git",
    ".idea",
    ".vscode",
    ".cache",
    ".pytest_cache",
}


def should_ignore(name: str, is_dir: bool) -> bool:
    """Determine if a file or directory should be ignored."""
    if name.startswith("."):
        return True
    if name.startswith("_"):
        return True
    if name.startswith("__"):
        return True
    if is_dir and name in IGNORED_DIRS:
        return True
    return False


def list_directory_tree(root_dir: str, prefix: str = "") -> str:
    """
    Recursively builds and returns the directory tree of the given root directory.
    Use this to visualize the project structure when a project root path is available.
    Returns an empty string if root_dir does not exist or is inaccessible.
    """
    result = ""

    try:
        items = os.listdir(root_dir)
    except Exception as e:
        _ps_logger.error(f"Error accessing {root_dir}: {e}")
        return result

    filtered_items = []
    for item in items:
        path = os.path.join(root_dir, item)
        if should_ignore(item, os.path.isdir(path)):
            continue
        filtered_items.append(item)

    for index, item in enumerate(filtered_items):
        path = os.path.join(root_dir, item)
        connector = "└── " if index == len(filtered_items) - 1 else "├── "
        result += prefix + connector + item + "\n"

        if os.path.isdir(path):
            extension = "    " if index == len(filtered_items) - 1 else "│   "
            result += list_directory_tree(path, prefix + extension)

    return result


def read_file_content(file_path: str) -> str:
    """
    Opens a file and returns its full content as a string.
    Use this to read source files relevant to the reported error so the
    actual code can be inspected during root cause analysis.
    Returns an error message string if the file cannot be read.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        _ps_logger.error(f"Error reading file: {e}")
        return f"Error reading file: {e}"


_FILE_TOOLS = [FunctionTool(list_directory_tree), FunctionTool(read_file_content)]

_ps_logger.debug("File inspection tools defined.")


# ─────────────────────────────────────────────────────────────
# MCP TOOLSETS
# ─────────────────────────────────────────────────────────────
file_system_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP\file_system_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP",
        ),
        timeout_in_seconds=30,
    )
)

# ─────────────────────────────────────────────────────────────
# SEARCH WORKER
# Query passed directly as constructor arg — no state key race condition.
# ─────────────────────────────────────────────────────────────
class PSSearchWorker(BaseAgent):
    """Runs a single google_search query and returns result via event stream."""

    worker_index: int
    query: str

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, *, name: str, worker_index: int, query: str):
        super().__init__(name=name, worker_index=worker_index, query=query)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        _ps_logger.info(f"[{self.name}] Searching → '{self.query}'")

        # Build instruction via concatenation — NOT an f-string.
        # ADK's inject_session_state re-scans the instruction string for {var}
        # patterns AFTER Python has already resolved the f-string, so any { }
        # chars remaining (from the query text itself) trigger a KeyError.
        # Plain concatenation produces a string with no { } tokens at all.
        inner_instruction = (
            "You are a technical research assistant.\n"
            "Use the google_search tool to search for: \"" + _sanitize_for_instruction(self.query) + "\"\n"
            "\n"
            "Focus on:\n"
            "- Official documentation, GitHub issues, Stack Overflow answers\n"
            "- Error explanations and root causes\n"
            "- Step-by-step fixes and verified solutions\n"
            "- Version-specific fixes if relevant\n"
            "\n"
            "Return a detailed, structured summary of findings.\n"
            "Include source names, code snippets if found, and solution steps.\n"
            "Output ONLY the summary — no preamble.\n"
        )

        inner = LlmAgent(
            name=f"ps_inner_search_{self.worker_index}",
            model=RESEARCH_MODEL,
            instruction=inner_instruction,
            tools=[google_search],
        )

        result_text = ""
        async for event in inner.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result_text += part.text

        _ps_logger.info(f"[{self.name}] Result length: {len(result_text)} chars")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=result_text or "No result.")],
            ),
        )


_ps_logger.debug("PSSearchWorker defined.")


# ─────────────────────────────────────────────────────────────
# PUBLIC WRAPPER — ProblemSolverAgent (BaseAgent)
#
# All orchestration in Python — no SequentialAgent.
# Query builder output captured directly from event stream.
# Search results captured directly from parallel event stream.
# ─────────────────────────────────────────────────────────────
class ProblemSolverAgent(BaseAgent):
    """
    Analyses programming errors, stack traces, exceptions, bugs, crashes,
    configuration issues, and technical problems. Identifies root causes
    using mandatory Google Search and knowledge base, then provides
    step-by-step solutions in a structured markdown report.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="problem_solver_agent",
            description=(
                "Analyses programming errors, stack traces, exceptions, bugs, crashes, "
                "configuration issues, and technical problems. Identifies root causes "
                "using Google Search and knowledge base, then provides step-by-step "
                "solutions. Use for any error message, bug report, or technical issue."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        _ps_logger.info("[ProblemSolverAgent] Pipeline started.")

        # ── STEP 1: Capture problem statement
        problem = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    problem += part.text

        if not problem:
            problem = ctx.session.state.get(PS_KEY_PROBLEM, "")
            if problem:
                _ps_logger.info("[ProblemSolverAgent] Problem recovered from state.")

        if not problem:
            _ps_logger.warning("[ProblemSolverAgent] No problem statement found.")
        else:
            _ps_logger.info(
                f"[ProblemSolverAgent] Problem captured ({len(problem)} chars): "
                f"'{problem[:120]}{'...' if len(problem) > 120 else ''}'"
            )

        ctx.session.state[PS_KEY_PROBLEM] = problem
        current_year = datetime.datetime.now().year

        # ── STEP 2: Run analyser — capture output directly from event stream
        # NOT via output_key/SequentialAgent (unreliable state flush in this ADK version).
        #
        # Instructions are built with plain string concatenation — NOT f-strings.
        # ADK's inject_session_state re-scans the instruction string for {var}
        # patterns and raises KeyError if the variable is absent from session state.
        # Stack traces, logs, and JSON all contain { } chars. Concatenation
        # produces a string with no { } tokens so ADK's scanner finds nothing.
        analyser_instruction = (
            "You are an expert Technical Problem Analyst.\n"
            "\n"
            "Problem statement:\n"
            + _sanitize_for_instruction(problem) + "\n"
            "\n"
            "Your job:\n"
            "PART A — Analyse the problem:\n"
            "- Identify problem type (runtime error, config issue, logic bug, dependency conflict, etc.)\n"
            "- Identify technology stack (language, framework, library, OS, etc.)\n"
            "- List most likely root causes based on your knowledge.\n"
            "\n"
            "PART B — Generate " + str(MIN_QUERIES) + " to " + str(MAX_QUERIES) + " highly targeted Google search queries:\n"
            "- Cover BOTH root cause investigation AND solution/fix finding.\n"
            "- Be specific — include error codes, library names, version hints if present.\n"
            "- Mix angles: \"cause of X\", \"fix for X\", \"X solution\", \"X error stackoverflow " + str(current_year) + "\".\n"
            "\n"
            "Output ONLY a numbered list of search queries — nothing else, no explanation, no preamble:\n"
            "1. first search query\n"
            "2. second search query\n"
            "3. third search query\n"
            "...\n"
        )

        analyser = LlmAgent(
            name="ps_analyser_agent",
            model=RESEARCH_MODEL,
            instruction=analyser_instruction,
        )

        raw_query_text = ""
        async for event in analyser.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        raw_query_text += part.text

        _ps_logger.debug(f"[ProblemSolverAgent] raw_query_text:\n{raw_query_text}")

        # ── STEP 3: Parse numbered list into Python list
        queries: List[str] = []
        for line in raw_query_text.strip().splitlines():
            line = line.strip()
            match = re.match(r"^\d+[\.\)]\s+(.+)$", line)
            if match:
                q = match.group(1).strip()
                if q:
                    queries.append(q)

        _ps_logger.info(f"[ProblemSolverAgent] Parsed {len(queries)} queries.")

        # Pad if under minimum
        if len(queries) < MIN_QUERIES:
            _ps_logger.warning(
                f"[ProblemSolverAgent] Padding queries from {len(queries)} to {MIN_QUERIES}."
            )
            fallbacks = [
                f"{problem[:80]} fix {current_year}",
                f"{problem[:80]} root cause solution",
                f"{problem[:80]} stackoverflow",
            ]
            while len(queries) < MIN_QUERIES:
                pad = fallbacks[len(queries) % len(fallbacks)]
                queries.append(pad if pad not in queries else f"{problem[:60]} solution part {len(queries)+1}")

        queries = queries[:MAX_QUERIES]

        _ps_logger.info(f"[ProblemSolverAgent] Final query count: {len(queries)}")
        for i, q in enumerate(queries):
            _ps_logger.info(f"  [{i}] {q}")

        # ── STEP 4: Run parallel searches — collect results from event stream
        workers = [
            PSSearchWorker(name=f"ps_search_worker_{i}", worker_index=i, query=q)
            for i, q in enumerate(queries)
        ]

        parallel = ParallelAgent(name="ps_parallel_search_agent", sub_agents=workers)

        worker_names = {f"ps_search_worker_{i}" for i in range(len(queries))}
        worker_results: dict = {}  # worker_name → text

        _ps_logger.info(f"[ProblemSolverAgent] Running {len(workers)} parallel searches.")
        async for event in parallel.run_async(ctx):
            if (
                event.author in worker_names
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
                    _ps_logger.info(
                        f"[ProblemSolverAgent] Captured result from {event.author}: {len(text)} chars"
                    )

        # Build ordered results list
        results_list: List[str] = []
        for i, q in enumerate(queries):
            text = worker_results.get(f"ps_search_worker_{i}", "")
            if text:
                results_list.append(f"[Search {i+1}: {q}]\n{text}")

        _ps_logger.info(f"[ProblemSolverAgent] Collected {len(results_list)} non-empty results.")

        # ── STEPS 5 & 6: File inspection — list directory tree + read relevant files
        #
        # An LlmAgent is given the two FunctionTools (list_directory_tree,
        # read_file_content) and instructed to:
        #   • Call list_directory_tree if a project root path is detectable from
        #     the problem statement (e.g. a file path, import path, traceback line).
        #   • Call read_file_content on any source file that appears directly
        #     linked to the error (e.g. the file named in the traceback).
        #   • Skip both calls if no relevant path information is present.
        #
        # The agent's output — tree + file contents — is captured from the event
        # stream using the same pattern used for the analyser and search workers.
        # ─────────────────────────────────────────────────────────────────────────
        file_inspector_instruction = (
            "You are a File Inspector assistant helping to debug a technical problem.\n"
            "\n"
            "Problem statement:\n"
            + _sanitize_for_instruction(problem) + "\n"
            "\n"
            "Your job — follow these steps IN ORDER:\n"
            "\n"
            "STEP 1 — Project directory tree:\n"
            "  - Look at the problem statement for any file paths, import paths,\n"
            "    or tracebacks that reveal the project root folder.\n"
            "  - If you can identify the project root, call list_directory_tree(root_dir=<path>)\n"
            "    to visualise the project structure.\n"
            "  - If no project root can be determined, skip this step and say so.\n"
            "\n"
            "STEP 2 — Read relevant source file(s):\n"
            "  - Identify the specific file(s) mentioned in the error / traceback\n"
            "    (e.g. the file on the last traceback line, or the file the user mentioned).\n"
            "  - For each such file, call read_file_content(file_path=<absolute_path>)\n"
            "    so that the actual source code can be inspected.\n"
            "  - If no specific file can be identified from the problem statement, skip\n"
            "    this step and say so.\n"
            "\n"
            "Output format:\n"
            "  - If you listed the tree, include it under the heading: ## Directory Tree\n"
            "  - If you read file(s), include each under: ## File: <path>\n"
            "  - If you skipped both steps, output exactly: NO_FILE_CONTEXT\n"
            "  - Do NOT add any other commentary or preamble.\n"
        )

        file_inspector = LlmAgent(
            name="ps_file_inspector_agent",
            model=RESEARCH_MODEL,
            instruction=file_inspector_instruction,
            tools=_FILE_TOOLS,
        )

        file_context = ""
        _ps_logger.info("[ProblemSolverAgent] Running file inspector agent.")
        async for event in file_inspector.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        file_context += part.text

        file_context = file_context.strip()

        if not file_context or file_context == "NO_FILE_CONTEXT":
            _ps_logger.info("[ProblemSolverAgent] File inspector: no file context available.")
            file_context = ""
        else:
            _ps_logger.info(
                f"[ProblemSolverAgent] File inspector produced {len(file_context)} chars of context."
            )

        # ── STEP 7: Build solution agent with everything embedded in the prompt.
        # Search results and file content may contain { } (JSON, code snippets) — escape them.
        search_block = "\n\n".join(results_list) if results_list else "No search results available."

        # Build file context section — only included when the inspector found something.
        if file_context:
            file_context_section = (
                "\n"
                "--- PROJECT FILE CONTEXT ---\n"
                + _sanitize_for_instruction(file_context) + "\n"
                "--- END OF FILE CONTEXT ---\n"
            )
        else:
            file_context_section = ""

        # Build instruction via concatenation — NOT an f-string.
        # Both search_block and file_context may contain code snippets / JSON with
        # { } chars that would break ADK's inject_session_state scanner.
        solution_instruction = (
            "You are a Senior Software Engineer and Debugging Expert.\n"
            "\n"
            "Problem Statement:\n"
            + _sanitize_for_instruction(problem) + "\n"
            "\n"
            "--- GOOGLE SEARCH RESULTS ---\n"
            + _sanitize_for_instruction(search_block) + "\n"
            "--- END OF SEARCH RESULTS ---\n"
            + file_context_section
            + "\n"
            "Using the search results above"
            + (" and the project file context" if file_context else "")
            + " AND your own technical knowledge, produce a complete\n"
            "solution report in markdown:\n"
            "\n"
            "## Problem Summary\n"
            "(Restate the problem clearly in 2-3 sentences)\n"
            "\n"
            "## Root Cause Analysis\n"
            "### Primary Root Cause\n"
            "(The most likely cause — explain WHY it produces this problem)\n"
            "\n"
            "### Secondary Possible Causes\n"
            "(Other contributing factors)\n"
            "\n"
            "## Solution\n"
            "\n"
            "### Primary Fix\n"
            "(Main recommended solution with step-by-step instructions.\n"
            " Include exact commands, code snippets, configuration changes.)\n"
            "\n"
            "### Alternative Solutions\n"
            "(1-3 other approaches if the primary fix does not work)\n"
            "\n"
            "## Prevention\n"
            "(Best practices to avoid this problem in future)\n"
            "\n"
            "## Verification\n"
            "(How to confirm the fix worked — test commands, expected outputs)\n"
            "\n"
            "## References\n"
            "(Search queries and sources that informed this solution)\n"
            "\n"
            "RULES:\n"
            "- Be precise and actionable — every step must be executable.\n"
            "- Include code blocks with triple backticks where relevant.\n"
            "- Do NOT fabricate solutions not supported by search results or your knowledge.\n"
            "- If multiple solutions exist, rank them by reliability.\n"
        )

        solution_agent = LlmAgent(
            name="ps_solution_agent",
            model=RESEARCH_MODEL,
            instruction=solution_instruction,
            output_key=PS_KEY_SOLUTION_REPORT,
        )

        final_solution = ""
        async for event in solution_agent.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_solution += part.text

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
