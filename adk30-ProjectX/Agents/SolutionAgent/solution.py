# solution.py
# ─────────────────────────────────────────────────────────────
# Solution Agent Module (ADK Native Workflow)
#
# Flow:
#   1. Capture problem statement from user content = problem_statement + directory_structure(optional) + file_content(optional)
#   2. Get current datetime (Python — never via LLM tool)
#   3. Context Classifier LLM → decide if project files/structure
#      are needed to produce an accurate solution
#      • If YES → yield a CONTEXT_REQUEST response listing exactly
#        what the root agent must fetch (files, directory listings)
#        and STOP. Root agent reads files via file_system_mcp and
#        calls this agent again with problem + fetched context.
#      • If NO  → proceed directly to Step 4.
#   4. Query Builder LLM → 2–8 targeted Google search queries
#      (captured from event stream — NOT output_key/SequentialAgent)
#   5. Parallel Search → one LlmAgent worker per query
#      (results stored in state via output_key — NOT from event stream)
#   6. Solution LLM → problem + context + search results injected
#      → structured markdown solution report
#   7. Action Plan LLM → converts solution into a machine-readable
#      step-by-step plan for root agent to execute using
#      code_agent and file_system_mcp
#
# Google Search is ALWAYS mandatory — every problem gets searched.
# ─────────────────────────────────────────────────────────────

import os
import re
import logging
import datetime
from pathlib import Path
from typing import AsyncGenerator, List

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.events import Event, EventActions
from google.adk.tools.google_search_tool import google_search
from google.adk.apps import App
from google.genai import types

from .config import config

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "log"
_LOG_DIR.mkdir(exist_ok=True)

_log_filepath = _LOG_DIR / (
    datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S") + "_solution.log"
)
_formatter = logging.Formatter(
    "%(asctime)s  [%(module)s]  %(levelname)-8s  %(name)s  %(message)s"
)

logger = logging.getLogger("solution_agent")
logger.setLevel(logging.DEBUG)
logger.propagate = False

_fh = logging.FileHandler(_log_filepath, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_formatter)
logger.addHandler(_fh)

_ch = logging.StreamHandler()
_ch.setLevel(logging.DEBUG)
_ch.setFormatter(_formatter)
logger.addHandler(_ch)

logger.info(f"Solution Agent initialised → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
RESEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

MIN_QUERIES = 2
MAX_QUERIES = 8

# ─────────────────────────────────────────────────────────────
# STATE KEYS
# ─────────────────────────────────────────────────────────────
KEY_PROBLEM          = "solution:problem"
KEY_CURRENT_DATETIME = "solution:current_datetime"
KEY_PROJECT_CONTEXT  = "solution:project_context"   # fetched file content
KEY_SOLUTION_REPORT  = "solution:solution_report"
KEY_ACTION_PLAN      = "solution:action_plan"

# Sentinel prefix that root agent detects to trigger file fetching
CONTEXT_REQUEST_PREFIX = "##CONTEXT_REQUEST##"


# ─────────────────────────────────────────────────────────────
# HELPER — callable instruction wrapper
#
# Wraps a pre-built string in a callable so ADK sets
# bypass_state_injection = True and NEVER runs inject_session_state().
# This is the only reliable fix for { } in stack traces / search results.
# ─────────────────────────────────────────────────────────────
def _make_instruction(text: str):
    def _fn(_ctx: ReadonlyContext) -> str:
        return text
    return _fn


# ─────────────────────────────────────────────────────────────
# HELPER — extract file contents from session events
#
# When root agent reads files via file_system_mcp and then calls
# solution_agent, the file contents live in the session event stream
# as function_response parts — NOT in user_content. This helper
# scans all session events and assembles a ## PROVIDED CONTEXT block
# so SolutionAgent is never dependent on root agent assembling the
# combined string correctly.
# ─────────────────────────────────────────────────────────────
def _extract_context_from_session(ctx: InvocationContext) -> str:
    file_sections = []
    for event in ctx.session.events:
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            fr = getattr(part, "function_response", None)
            if fr is None:
                continue
            tool_name = getattr(fr, "name", "") or ""
            # Only file read / directory list responses
            if not any(k in tool_name.lower() for k in ("read", "list", "get")):
                continue
            response = getattr(fr, "response", None)
            if not response:
                continue

            text_content = ""
            file_path = tool_name

            if isinstance(response, dict):
                # Shape A: {'content': [{'type': 'text', 'text': '...'}], 'path': '...'}
                # Shape B: {'content': '...', 'path': '...'}
                # Shape C: {'result': '...'}
                raw = response.get(
                    "content",
                    response.get("result", response.get("output", "")),
                )
                if isinstance(raw, list):
                    for item in raw:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                elif isinstance(raw, str):
                    text_content = raw
                file_path = str(
                    response.get("path", response.get("file", tool_name))
                )
            elif isinstance(response, str):
                text_content = response

            text_content = text_content.strip()
            if text_content and len(text_content) > 20:
                file_sections.append(
                    f"### File: {file_path}\n```\n{text_content}\n```"
                )
                logger.debug(
                    f"[extract_context] Found '{file_path}': {len(text_content)} chars"
                )

    if not file_sections:
        return ""
    return "## PROVIDED CONTEXT\n\n" + "\n\n".join(file_sections)


# ─────────────────────────────────────────────────────────────
# SEARCH WORKER FACTORY
#
# Returns a plain LlmAgent for one search query.
# Using include_contents="none" so the worker only sees its own
# instruction — no accumulated session history from previous inner
# agents. Results are written to state via output_key so the parent
# reads them from state after the parallel run completes, avoiding
# unreliable event-stream capture across parallel branches.
# ─────────────────────────────────────────────────────────────
def _make_search_worker(index: int, query: str) -> LlmAgent:
    prompt = (
        "You are a technical debugging research assistant.\n\n"
        "Use the google_search tool to search for:\n"
        "\"" + query + "\"\n\n"
        "Focus on:\n"
        "- Official documentation and changelogs\n"
        "- GitHub issues, pull requests, and confirmed bug reports\n"
        "- Stack Overflow answers (accepted and highly upvoted)\n"
        "- Confirmed root causes and error explanations\n"
        "- Step-by-step fixes, workarounds, and verified solutions\n"
        "- Version-specific fixes and compatibility notes\n\n"
        "Return a detailed, structured summary of findings.\n"
        "Include source names, exact commands or code snippets, and solution steps.\n"
        "Output ONLY the factual summary — no preamble, no opinions.\n"
    )
    return LlmAgent(
        name=f"solution_search_worker_{index}",
        model=RESEARCH_MODEL,
        tools=[google_search],
        instruction=_make_instruction(prompt),
        include_contents="none",
        output_key=f"solution:result:{index}",
    )


# ─────────────────────────────────────────────────────────────
# SOLUTION AGENT
# ─────────────────────────────────────────────────────────────
class SolutionAgent(BaseAgent):
    """
    Analyses programming errors, stack traces, exceptions, bugs, crashes,
    configuration issues, and project-level technical problems.

    When project files are needed, it first returns a CONTEXT_REQUEST
    listing the exact files/directories root agent must fetch via
    file_system_mcp. On the second call (with context provided), it
    runs the full pipeline and returns a solution report + action plan
    that root agent executes using code_agent and file_system_mcp.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="solution_agent",
            description=(
                "Analyses programming errors, stack traces, exceptions, bugs, crashes, "
                "configuration issues, and project-level technical problems. When needed, "
                "requests project files from root agent via file_system_mcp for full context. "
                "Returns a structured solution report + an action plan for root agent to "
                "execute using code_agent and file_system_mcp."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info("[SolutionAgent] Pipeline started.")

        # ── STEP 0: Clear stale state from any previous task ─────
        # Each invocation of SolutionAgent is a fresh, independent task.
        # Stale state from a prior problem must never bleed into this one.
        for key in (
            KEY_PROBLEM, KEY_CURRENT_DATETIME, KEY_PROJECT_CONTEXT,
            KEY_SOLUTION_REPORT, KEY_ACTION_PLAN,
        ):
            ctx.session.state.pop(key, None)
        # Clear stale search results
        for k in list(ctx.session.state.keys()):
            if k.startswith("solution:result:"):
                ctx.session.state.pop(k, None)

        logger.info("[SolutionAgent] State cleared — starting fresh.")

        # ── STEP 1: Capture problem + any previously provided context ──
        #
        # Three cases handled here:
        #
        # Case A — First call, no prior CONTEXT_REQUEST:
        #   user_content = full problem/traceback. Parse normally.
        #
        # Case B — Root agent assembled context correctly (ideal):
        #   user_content = "<problem>\n## PROVIDED CONTEXT\n<files>"
        #
        # Case C — Root agent passed only its short instruction after
        #   CONTEXT_REQUEST (the common failure mode, e.g. "get the
        #   required content and pass it to the solution agent"):
        #   Detect by scanning session events for our own prior
        #   ##CONTEXT_REQUEST## response — extract the preserved
        #   problem text from that event + file contents from
        #   file_system_mcp function_response events that followed.

        raw_input = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    raw_input += part.text

        # Detect whether WE already sent a CONTEXT_REQUEST this session
        # by scanning session events for our own prior response.
        prior_context_request_text = ""
        for event in ctx.session.events:
            if (
                event.author == self.name
                and event.content
                and event.content.parts
            ):
                for part in event.content.parts:
                    txt = getattr(part, "text", None) or ""
                    if txt.startswith(CONTEXT_REQUEST_PREFIX):
                        prior_context_request_text = txt
                        # Keep scanning — take the LAST one

        context_request_sent = bool(prior_context_request_text)

        problem         = raw_input
        project_context = ""

        if "## PROVIDED CONTEXT" in raw_input:
            # Case B — root agent assembled it correctly
            split_parts = raw_input.split("## PROVIDED CONTEXT", 1)
            problem         = split_parts[0].strip()
            project_context = "## PROVIDED CONTEXT\n" + split_parts[1].strip()
            logger.info(
                f"[SolutionAgent] Project context found in user_content "
                f"({len(project_context)} chars)."
            )

        elif context_request_sent:
            # Case C — recover problem from the preserved text at the bottom
            # of the CONTEXT_REQUEST event ("Original problem preserved below...")
            if "Original problem preserved below for re-submission:" in prior_context_request_text:
                problem = prior_context_request_text.split(
                    "Original problem preserved below for re-submission:", 1
                )[1].strip()
            else:
                # Fallback: strip the preamble, take everything after the file list
                problem = raw_input

            logger.info(
                f"[SolutionAgent] Problem recovered from prior CONTEXT_REQUEST event "
                f"({len(problem)} chars). user_content was: '{raw_input[:80]}'"
            )

            project_context = _extract_context_from_session(ctx)
            if project_context:
                logger.info(
                    f"[SolutionAgent] Context extracted from session events "
                    f"({len(project_context)} chars)."
                )
            else:
                logger.warning(
                    "[SolutionAgent] Could not extract context from session events — "
                    "proceeding without project files."
                )

        else:
            # Case A — first call, no prior CONTEXT_REQUEST
            if not raw_input:
                logger.warning("[SolutionAgent] No input found.")

        logger.info(
            f"[SolutionAgent] Problem ({len(problem)} chars): "
            f"'{problem[:120]}{'...' if len(problem) > 120 else ''}'"
        )
        logger.info(
            f"[SolutionAgent] Project context: "
            f"{'present (' + str(len(project_context)) + ' chars)' if project_context else 'none'}"
        )

        # ── STEP 2: Get current datetime ─────────────────────
        current_datetime = datetime.datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        current_year = datetime.datetime.now().year
        logger.info(f"[SolutionAgent] current_datetime='{current_datetime}'")

        # ── STEP 3: Context Classifier ────────────────────────
        # Ask the LLM: does this problem require reading project
        # files or directory structure to diagnose accurately?
        # Only runs if context has NOT already been provided AND
        # this is the first call (no prior CONTEXT_REQUEST sent).
        # If a CONTEXT_REQUEST was already sent we never ask again —
        # this prevents an infinite CONTEXT_REQUEST loop when file
        # extraction from session events partially fails.
        if not project_context and not context_request_sent:
            logger.info("[SolutionAgent] No context provided — running classifier.")

            classifier_prompt = (
                "You are a technical problem triage assistant.\n\n"
                "Problem statement:\n"
                + problem + "\n\n"
                "Your task: decide whether solving this problem accurately requires "
                "reading the project's actual source files or directory structure.\n\n"
                "Answer YES if the problem involves ANY of these:\n"
                "- Import errors, module not found, circular imports\n"
                "- Wrong file paths, missing files, misconfigured directories\n"
                "- Code bugs where the actual source code must be seen to diagnose\n"
                "- Configuration errors (wrong values in config files)\n"
                "- Dependency version conflicts visible in requirements.txt / pyproject.toml\n"
                "- Project structure issues (missing __init__.py, wrong package layout)\n"
                "- Any error where seeing the actual code or config would change the diagnosis\n\n"
                "Answer NO if the problem can be solved purely from the error message, "
                "traceback, and web search — no file reading needed.\n\n"
                "If YES, also list EXACTLY which files or directories should be read.\n"
                "Use real relative paths if visible in the traceback, otherwise use "
                "descriptive names like 'project root directory listing', "
                "'the file mentioned in the traceback', etc.\n\n"
                "Respond in this EXACT format — nothing else:\n\n"
                "NEEDS_CONTEXT: YES\n"
                "FILES_NEEDED:\n"
                "- path/to/file1.py\n"
                "- path/to/file2.py\n"
                "- directory listing of: src/\n\n"
                "OR:\n\n"
                "NEEDS_CONTEXT: NO\n"
            )

            classifier = LlmAgent(
                name="solution_context_classifier",
                model=RESEARCH_MODEL,
                instruction=_make_instruction(classifier_prompt),
                include_contents="none",
            )

            classifier_output = ""
            async for event in classifier.run_async(ctx):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            classifier_output += part.text

            logger.debug(f"[SolutionAgent] Classifier output:\n{classifier_output}")

            needs_context = "NEEDS_CONTEXT: YES" in classifier_output.upper()

            if needs_context:
                # Extract the files/dirs needed
                files_section = ""
                if "FILES_NEEDED:" in classifier_output:
                    files_section = classifier_output.split("FILES_NEEDED:", 1)[1].strip()

                logger.info("[SolutionAgent] Context required — yielding CONTEXT_REQUEST.")

                context_request_body = (
                    CONTEXT_REQUEST_PREFIX + "\n\n"
                    "Before I can produce an accurate solution, I need to read the "
                    "following files and/or directories from the project.\n\n"
                    "**Please use file_system_mcp to fetch each item below, then "
                    "call me again with the original problem followed by:**\n\n"
                    "```\n"
                    "## PROVIDED CONTEXT\n"
                    "<paste each file's full content here, labelled with its path>\n"
                    "```\n\n"
                    "**Files / directories needed:**\n"
                    + files_section + "\n\n"
                    "---\n"
                    "_Original problem preserved below for re-submission:_\n\n"
                    + problem
                )

                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=context_request_body)],
                    ),
                )
                # Stop here — root agent will re-invoke with context
                return

            else:
                logger.info("[SolutionAgent] No context required — proceeding to search.")

        else:
            if project_context:
                logger.info("[SolutionAgent] Context already provided — skipping classifier.")
            else:
                logger.info("[SolutionAgent] Prior CONTEXT_REQUEST sent — skipping classifier, proceeding with available data.")

        # ── STEP 4: Query builder ─────────────────────────────
        # include_contents="none" — instruction already contains the full
        # problem; session history from the classifier must not leak in.
        context_hint = (
            "\nProject context has been provided and should inform the search queries.\n"
            if project_context else ""
        )

        query_builder_prompt = (
            "You are an expert Technical Search Query Planner.\n\n"
            "Current date and time: " + current_datetime + "\n"
            + context_hint +
            "Problem statement:\n"
            + problem + "\n\n"
            "Your job: generate between " + str(MIN_QUERIES) + " and " + str(MAX_QUERIES) + " "
            "highly targeted and diverse Google search queries that together give "
            "complete coverage of this problem — both for understanding the root cause "
            "AND for finding verified, actionable solutions.\n\n"
            "Rules:\n"
            "- Each query must target a completely different angle.\n"
            "- Be specific — include exact error codes, library/framework names, "
            "and version numbers if visible in the problem.\n"
            "- Mix angles: root cause investigation, official fix, workaround, "
            "migration guide, known issue tracker, Stack Overflow answer.\n"
            "- Include the current year (" + str(current_year) + ") in at least some queries.\n\n"
            "Output ONLY a numbered list — no explanation, no preamble:\n"
            "1. first search query\n"
            "2. second search query\n"
            "3. third search query\n"
        )

        query_builder = LlmAgent(
            name="solution_query_builder_agent",
            model=RESEARCH_MODEL,
            instruction=_make_instruction(query_builder_prompt),
            include_contents="none",
        )

        raw_query_text = ""
        async for event in query_builder.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        raw_query_text += part.text

        logger.debug(f"[SolutionAgent] raw_query_text:\n{raw_query_text}")

        # ── STEP 5: Parse queries ─────────────────────────────
        queries: List[str] = []
        for line in raw_query_text.strip().splitlines():
            match = re.match(r"^\d+[\.\)]\s+(.+)$", line.strip())
            if match:
                q = match.group(1).strip()
                if q:
                    queries.append(q)

        logger.info(f"[SolutionAgent] Parsed {len(queries)} queries.")

        if len(queries) < MIN_QUERIES:
            logger.warning(f"[SolutionAgent] Padding queries to {MIN_QUERIES}.")
            problem_short = problem[:80].strip()
            fallbacks = [
                f"{problem_short} fix {current_year}",
                f"{problem_short} root cause solution",
                f"{problem_short} stackoverflow {current_year}",
            ]
            while len(queries) < MIN_QUERIES:
                pad = fallbacks[len(queries) % len(fallbacks)]
                queries.append(
                    pad if pad not in queries
                    else f"{problem_short} solution part {len(queries) + 1}"
                )

        queries = queries[:MAX_QUERIES]
        logger.info(f"[SolutionAgent] Final queries ({len(queries)}):")
        for i, q in enumerate(queries):
            logger.info(f"  [{i}] {q}")

        # ── STEP 6: Parallel search ───────────────────────────
        # Workers are plain LlmAgents (no BaseAgent wrapper).
        # Each worker uses include_contents="none" + output_key so results
        # are written directly to state — no fragile event-stream capture.
        workers = [_make_search_worker(i, q) for i, q in enumerate(queries)]
        parallel = ParallelAgent(
            name="solution_parallel_search_agent", sub_agents=workers
        )

        logger.info(f"[SolutionAgent] Running {len(workers)} parallel searches.")
        async for _ in parallel.run_async(ctx):
            pass  # Results stored in state via each worker's output_key

        # Read all search results from state after parallel run completes
        results_list: List[str] = []
        for i, q in enumerate(queries):
            text = ctx.session.state.get(f"solution:result:{i}", "").strip()
            if text:
                results_list.append(f"[Search {i + 1}: {q}]\n{text}")
                logger.info(
                    f"[SolutionAgent] Captured worker {i}: {len(text)} chars"
                )

        logger.info(f"[SolutionAgent] Collected {len(results_list)} non-empty results.")

        # ── STEP 7: Solution writer — full context injected ───
        # include_contents="none" — the entire prompt is self-contained;
        # none of the accumulated classifier / query-builder / search
        # history should leak into this LLM call.
        search_block = (
            "\n\n".join(results_list) if results_list
            else "No search results available."
        )

        context_block = (
            "\n\n" + project_context + "\n"
            if project_context
            else "\nNo project files were provided.\n"
        )

        solution_prompt = (
            "You are a Senior Software Engineer and Debugging Expert.\n\n"
            "Current date and time: " + current_datetime + "\n\n"
            "━━━ PROBLEM STATEMENT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + problem + "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + context_block +
            "━━━ GOOGLE SEARCH RESULTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + search_block + "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Using ALL of the above — project files, search results, and your own "
            "technical knowledge — produce a complete solution report in markdown.\n\n"
            "## Problem Summary\n"
            "(Restate the problem in 2–3 sentences. Identify the technology stack, "
            "error type, and context.)\n\n"
            "## Root Cause Analysis\n\n"
            "### Primary Root Cause\n"
            "(The most likely cause — explain WHY it produces this problem. "
            "Reference specific lines/files from the provided context if available.)\n\n"
            "### Secondary Possible Causes\n"
            "(Other contributing factors or alternative explanations.)\n\n"
            "## Solution\n\n"
            "### Primary Fix\n"
            "(Step-by-step instructions. Include exact commands and config changes.)\n\n"
            "### Complete Fixed Files\n"
            "⚠️  MANDATORY — For EVERY file that must be created or modified, output its "
            "COMPLETE content here as a named code block. Never truncate. Never use "
            "'# ... rest unchanged' or similar placeholders.\n"
            "Use this exact format for each file:\n\n"
            "#### `path/to/file.py`\n"
            "```python\n"
            "<complete file content — every line, first to last>\n"
            "```\n\n"
            "If multiple files need changes, repeat this block for each one.\n"
            "This is NOT optional — the action plan depends entirely on this section "
            "to write the files to disk.\n\n"
            "### Alternative Solutions\n"
            "(1–3 other approaches if the primary fix does not work.)\n\n"
            "## Prevention\n"
            "(Best practices and patterns to avoid this problem in the future.)\n\n"
            "## Verification\n"
            "(How to confirm the fix worked — test commands, expected outputs, "
            "log lines to look for.)\n\n"
            "## References\n"
            "(Search queries used and key sources that informed this solution.)\n\n"
            "RULES:\n"
            "- Be precise and actionable — every step must be immediately executable.\n"
            "- Use triple-backtick code blocks for all commands and code.\n"
            "- Do NOT fabricate solutions — only recommend what is supported by "
            "the search results, provided context, or your verified knowledge.\n"
            "- Complete Fixed Files section is MANDATORY — never skip it.\n"
            "- Every file block must be COMPLETE — no truncation, no '...',\n"
            "  no '# rest of file unchanged'. Root agent writes these directly to disk.\n"
        )

        solution_writer = LlmAgent(
            name="solution_writer_agent",
            model=RESEARCH_MODEL,
            instruction=_make_instruction(solution_prompt),
            output_key=KEY_SOLUTION_REPORT,
            include_contents="none",
        )

        final_solution = ""
        async for event in solution_writer.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_solution += part.text

        if not final_solution:
            final_solution = ctx.session.state.get(KEY_SOLUTION_REPORT, "")
            if final_solution:
                logger.info("[SolutionAgent] Solution recovered from state.")

        if not final_solution:
            final_solution = "Problem analysis complete. No solution report was generated."
            logger.warning("[SolutionAgent] Solution writer produced no output.")

        # ── STEP 8: Action Plan — instructions for root agent ─
        # include_contents="none" — instruction is fully self-contained.
        action_plan_prompt = (
            "You are a technical project execution planner.\n\n"
            "Below is a solution report produced by a Senior Software Engineer. "
            "The report contains a '### Complete Fixed Files' section with the "
            "full content of every file that must be written to disk.\n\n"
            "Solution report:\n"
            + final_solution + "\n\n"
            "The root agent has access to ONLY these tools:\n"
            "  • file_system_mcp  — write_file, edit_file, read_file, "
            "create_directory, delete_file, list_files\n\n"
            "CRITICAL RULES:\n"
            "1. Do NOT include any [code_agent] steps. code_agent is a sub-agent, "
            "not a tool, and cannot be called from an action plan.\n"
            "2. For every file in '### Complete Fixed Files', produce one "
            "[file_system_mcp] write_file step.\n"
            "3. Copy the COMPLETE file content from the report into the step — "
            "word for word, no truncation, no '...' or placeholders.\n"
            "4. Each step must be ONE discrete file_system_mcp operation.\n"
            "5. Label every step: [file_system_mcp].\n"
            "6. Order: create_directory steps first, then write_file steps.\n"
            "7. Final step: list_files on the affected directory to verify.\n"
            "8. If no file changes are needed, write: "
            "ACTION PLAN: No file changes required.\n\n"
            "Output format (markdown):\n\n"
            "## Action Plan\n\n"
            "### Step 1 — [file_system_mcp]\n"
            "**Operation:** write_file\n"
            "**File:** `exact/path/to/file.py`\n"
            "**Content:**\n"
            "```python\n"
            "<paste the COMPLETE file content here — never truncated>\n"
            "```\n\n"
            "### Step 2 — [file_system_mcp]\n"
            "**Operation:** list_files\n"
            "**Path:** `exact/path/to/directory`\n"
            "**Purpose:** Verify the file was written successfully.\n"
        )

        action_plan_agent = LlmAgent(
            name="solution_action_plan_agent",
            model=RESEARCH_MODEL,
            instruction=_make_instruction(action_plan_prompt),
            output_key=KEY_ACTION_PLAN,
            include_contents="none",
        )

        action_plan = ""
        async for event in action_plan_agent.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        action_plan += part.text

        if not action_plan:
            action_plan = ctx.session.state.get(KEY_ACTION_PLAN, "")

        logger.info(
            f"[SolutionAgent] Pipeline complete. "
            f"Solution: {len(final_solution)} chars. "
            f"Action plan: {len(action_plan)} chars."
        )

        # Combine solution report + action plan into single final output
        full_output = final_solution.rstrip() + "\n\n---\n\n" + action_plan.strip()

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=full_output)],
            ),
            actions=EventActions(
                state_delta={
                    KEY_SOLUTION_REPORT: final_solution,
                    KEY_ACTION_PLAN:     action_plan,
                }
            ),
        )


# ─────────────────────────────────────────────────────────────
# EXPORTS
# ─────────────────────────────────────────────────────────────
solution_agent = SolutionAgent()

app = App(
    name="solution_app",
    root_agent=solution_agent,
)

__all__ = ["solution_agent", "app", "CONTEXT_REQUEST_PREFIX"]
