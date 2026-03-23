# CodeXAgent/code.py
# ─────────────────────────────────────────────────────────────
# Code Agent — merged WRITE + FIX pipeline
#
# Flow:
#   0. Clear all state (each invocation is completely fresh)
#   1. Capture request from user_content
#      • Detect CONTEXT_REQUEST re-call via session events
#      • Recover request text + file contents from events
#      • If "## PROVIDED CONTEXT" present — split and use directly
#   2. Context Classifier → need existing files?
#      • YES → yield ##CONTEXT_REQUEST## and STOP
#      • NO  → continue
#   3. Mode Classifier → FIX or WRITE?
#   4. FIX path:
#      a. Query Builder → 2–8 search queries
#      b. Parallel Search → one LlmAgent per query, results in state
#      c. Fix Writer → solution report with Complete Fixed Files
#   4. WRITE path:
#      a. KB Classifier → relevant knowledge base tokens
#      b. Load KB files from disk
#      c. Task Planner → ordered FILE MANIFEST
#      d. File Writer → one LlmAgent per file, never truncated
#   5. Action Plan → file_system_mcp-only steps with inline content
#   6. Yield final output
#
# No chat history is maintained. Every inner LlmAgent uses
# include_contents="none". State is wiped at entry.
# ─────────────────────────────────────────────────────────────

import os
import re
import json
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
from .promptsx import (
    context_classifier_prompt,
    mode_classifier_prompt,
    kb_classifier_prompt,
    query_builder_prompt,
    search_worker_prompt,
    fix_writer_prompt,
    task_planner_prompt,
    file_writer_prompt,
    action_plan_prompt,
)

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "log"
_LOG_DIR.mkdir(exist_ok=True)

_log_filepath = _LOG_DIR / (
    datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S") + "_code.log"
)
_formatter = logging.Formatter(
    "%(asctime)s  [%(module)s]  %(levelname)-8s  %(name)s  %(message)s"
)

logger = logging.getLogger("codex_agent")
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

logger.info(f"Code Agent initialised → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
CODE_MODEL   = config.CODE_MODEL
SEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"]            = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

MIN_QUERIES = 2
MAX_QUERIES = 8

# ─────────────────────────────────────────────────────────────
# KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────
_KB_DIR: Path = Path(config.KNOWLEDGE_BASE)

KB_FILES: dict[str, str] = {
    p.stem.lower(): p.name
    for p in sorted(_KB_DIR.glob("*.md"))
    if p.is_file()
}

if KB_FILES:
    logger.info(f"KB loaded ({len(KB_FILES)}): {', '.join(sorted(KB_FILES))}")
else:
    logger.warning(f"No KB files found in: {_KB_DIR}")

# ─────────────────────────────────────────────────────────────
# STATE KEYS  (wiped at the start of every invocation)
# ─────────────────────────────────────────────────────────────
KEY_ACTION_PLAN = "code:action_plan"

# Sentinel root agent detects to trigger file fetching
CONTEXT_REQUEST_PREFIX = "##CONTEXT_REQUEST##"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _make_instruction(text: str):
    """Callable wrapper — bypasses ADK template scanner on { } chars."""
    def _fn(_ctx: ReadonlyContext) -> str:
        return text
    return _fn


def _load_kb(tokens: List[str]) -> str:
    sections: List[str] = []
    for token in tokens:
        filename = KB_FILES.get(token.lower())
        if not filename:
            continue
        filepath = _KB_DIR / filename
        if not filepath.exists():
            logger.warning(f"[CodeXAgent] KB file missing: {filepath}")
            continue
        content = filepath.read_text(encoding="utf-8")
        sections.append(f"### [{token.upper()} KB — {filename}]\n\n{content}")
        logger.info(f"[CodeXAgent] Loaded KB: {filename} ({len(content)} chars)")
    if not sections:
        return ""
    return "\n\n" + ("─" * 60 + "\n\n").join(sections)


def _parse_json_list(raw: str) -> List[str]:
    raw = raw.strip()
    try:
        cleaned = re.sub(r"^```[a-z]*\n?|```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(t).strip().lower() for t in parsed if str(t).strip()]
    except (json.JSONDecodeError, ValueError):
        pass
    return [t.strip().lower() for t in re.split(r"[,\n]+", raw) if t.strip()]


def _parse_file_manifest(raw: str) -> List[dict]:
    files = []
    for line in raw.strip().splitlines():
        match = re.match(r"^(?:\d+[\.\)]|-)\s+(\S+)\s+[—–-]+\s+(.+)$", line.strip())
        if match:
            files.append({
                "path":        match.group(1).strip(),
                "description": match.group(2).strip(),
            })
    return files


def _extract_context_from_session(ctx: InvocationContext, start_index: int = 0) -> str:
    """
    Scans session events from start_index onward for file_system_mcp
    function_response parts and assembles a ## PROVIDED CONTEXT block.
    start_index = index of the CONTEXT_REQUEST event so we only pick
    up file reads that belong to THIS task.
    """
    file_sections = []
    for event in ctx.session.events[start_index:]:
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            fr = getattr(part, "function_response", None)
            if fr is None:
                continue
            tool_name = getattr(fr, "name", "") or ""
            if not any(k in tool_name.lower() for k in ("read", "list", "get")):
                continue
            response = getattr(fr, "response", None)
            if not response:
                continue

            text_content = ""
            file_path    = tool_name

            if isinstance(response, dict):
                raw = response.get("content",
                      response.get("result",
                      response.get("output", "")))
                if isinstance(raw, list):
                    for item in raw:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                elif isinstance(raw, str):
                    text_content = raw
                file_path = str(response.get("path", response.get("file", tool_name)))
            elif isinstance(response, str):
                text_content = response

            text_content = text_content.strip()
            if text_content and len(text_content) > 20:
                file_sections.append(f"### File: {file_path}\n```\n{text_content}\n```")
                logger.debug(f"[extract_context] {file_path}: {len(text_content)} chars")

    if not file_sections:
        return ""
    return "## PROVIDED CONTEXT\n\n" + "\n\n".join(file_sections)


# ─────────────────────────────────────────────────────────────
# CODE AGENT
# ─────────────────────────────────────────────────────────────

class CodeXAgent(BaseAgent):
    """
    Unified code agent — writes new code AND fixes existing bugs.

    Modes (auto-detected per request):
      WRITE — builds new projects, scripts, APIs, components,
               or extends existing codebases.
      FIX   — diagnoses errors, tracebacks, and configuration
               issues; produces complete fixed files + action plan.

    No session history is maintained. Every invocation is fresh.
    Root agent provides context (files, errors) in user_content.
    Returns complete file content + a file_system_mcp-only Action Plan.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="codex_agent",
            description=(
                "Writes complete, production-quality code (new projects, scripts, APIs, "
                "full-stack apps) AND fixes bugs, errors, tracebacks, and configuration "
                "issues in existing projects. Supports Python, Go, JavaScript, TypeScript, "
                "Bash, Java, C++, Rust, SQL. Uses an internal knowledge base. Requests "
                "project files from root agent when needed. Returns complete file content "
                "and a file_system_mcp-only Action Plan for root agent to execute."
            ),
        )

    async def _llm(self, ctx: InvocationContext, name: str, prompt: str,
                   model: str = None, tools: list = None,
                   output_key: str = None) -> str:
        """Run one inner LlmAgent and return its text output."""
        kwargs = {}
        if tools:
            kwargs["tools"] = tools
        if output_key:
            kwargs["output_key"] = output_key
        agent = LlmAgent(
            name=name,
            model=model or CODE_MODEL,
            instruction=_make_instruction(prompt),
            include_contents="none",
            **kwargs,
        )
        result = ""
        async for event in agent.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result += part.text
        return result

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info("[CodeXAgent] Pipeline started.")

        # ── STEP 0: Wipe all stale state ─────────────────────
        for k in list(ctx.session.state.keys()):
            if k.startswith("code:"):
                ctx.session.state.pop(k, None)
        logger.info("[CodeXAgent] State cleared.")

        # ── STEP 1: Get input + detect CONTEXT_REQUEST re-call ─
        raw_input = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    raw_input += part.text

        # Scan session events for our own prior CONTEXT_REQUEST
        prior_cr_text  = ""
        cr_event_index = 0
        for idx, event in enumerate(ctx.session.events):
            if event.author == self.name and event.content and event.content.parts:
                for part in event.content.parts:
                    txt = getattr(part, "text", None) or ""
                    if txt.startswith(CONTEXT_REQUEST_PREFIX):
                        prior_cr_text  = txt
                        cr_event_index = idx  # keep last occurrence

        context_request_sent = bool(prior_cr_text)
        request         = raw_input
        project_context = ""

        if "## PROVIDED CONTEXT" in raw_input:
            # Root agent assembled it correctly
            parts = raw_input.split("## PROVIDED CONTEXT", 1)
            request         = parts[0].strip()
            project_context = "## PROVIDED CONTEXT\n" + parts[1].strip()
            logger.info(f"[CodeXAgent] Context in user_content ({len(project_context)} chars).")

        elif context_request_sent:
            # Root agent passed a short instruction — recover from events
            marker = "Original request preserved for re-submission:"
            if marker in prior_cr_text:
                request = prior_cr_text.split(marker, 1)[1].strip()
            else:
                request = raw_input
            logger.info(
                f"[CodeXAgent] Request from CONTEXT_REQUEST event ({len(request)} chars). "
                f"raw_input was: '{raw_input[:80]}'"
            )
            project_context = _extract_context_from_session(ctx, cr_event_index)
            if project_context:
                logger.info(f"[CodeXAgent] Context from session events ({len(project_context)} chars).")
            else:
                logger.warning("[CodeXAgent] No context in session events — proceeding without.")

        else:
            if not raw_input:
                logger.warning("[CodeXAgent] No input.")
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="Error: No request was provided.")],
                    ),
                )
                return

        logger.info(
            f"[CodeXAgent] Request ({len(request)} chars): "
            f"'{request[:120]}{'...' if len(request) > 120 else ''}'"
        )

        # ── STEP 2: Context Classifier ────────────────────────
        # Skip if context already provided OR prior CONTEXT_REQUEST sent
        if not project_context and not context_request_sent:
            logger.info("[CodeXAgent] Running context classifier.")
            cr_out = await self._llm(
                ctx, "code_context_classifier",
                context_classifier_prompt(request),
            )
            logger.debug(f"[CodeXAgent] Context classifier:\n{cr_out}")

            first_line = next(
                (ln.strip() for ln in cr_out.splitlines() if ln.strip()), ""
            ).upper()

            if first_line.startswith("NEEDS_CONTEXT: YES"):
                files_section = ""
                if "FILES_NEEDED:" in cr_out:
                    files_section = cr_out.split("FILES_NEEDED:", 1)[1].strip()

                body = (
                    CONTEXT_REQUEST_PREFIX + "\n\n"
                    "Before I can produce accurate output, I need to read the following "
                    "files and/or directories from the project.\n\n"
                    "**Please use file_system_mcp to fetch each item below, then "
                    "call me again with the original request followed by:**\n\n"
                    "```\n## PROVIDED CONTEXT\n"
                    "<paste each file's full content here, labelled with its path>\n```\n\n"
                    "**Files / directories needed:**\n"
                    + files_section + "\n\n"
                    "---\n"
                    "Original request preserved for re-submission:\n\n"
                    + request
                )
                logger.info("[CodeXAgent] Yielding CONTEXT_REQUEST.")
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=body)],
                    ),
                )
                return

        else:
            reason = "context provided" if project_context else "prior CONTEXT_REQUEST sent"
            logger.info(f"[CodeXAgent] Skipping context classifier ({reason}).")

        # ── STEP 3: Mode Classifier ───────────────────────────
        mode_raw = await self._llm(
            ctx, "code_mode_classifier",
            mode_classifier_prompt(request),
        )
        mode = "FIX" if "FIX" in mode_raw.strip().upper() else "WRITE"
        logger.info(f"[CodeXAgent] Mode: {mode}")

        current_datetime = datetime.datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        current_year     = datetime.datetime.now().year

        context_block = (
            "\n━━━ PROJECT CONTEXT (EXISTING FILES) ━━━━━━━━━━━━━━━━━━━━\n"
            + project_context
            + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            if project_context else ""
        )

        # ═════════════════════════════════════════════════════
        # FIX PATH
        # ═════════════════════════════════════════════════════
        if mode == "FIX":

            # ── 4a: Query Builder ─────────────────────────────
            context_hint = (
                "Project context has been provided and should inform the queries.\n"
                if project_context else ""
            )
            raw_queries = await self._llm(
                ctx, "code_query_builder",
                query_builder_prompt(
                    request, current_datetime, current_year,
                    context_hint, MIN_QUERIES, MAX_QUERIES,
                ),
            )

            queries: List[str] = []
            for line in raw_queries.strip().splitlines():
                m = re.match(r"^\d+[\.\)]\s+(.+)$", line.strip())
                if m and m.group(1).strip():
                    queries.append(m.group(1).strip())

            short = request[:80].strip()
            fallbacks = [
                f"{short} fix {current_year}",
                f"{short} root cause solution",
                f"{short} stackoverflow {current_year}",
            ]
            while len(queries) < MIN_QUERIES:
                queries.append(fallbacks[len(queries) % len(fallbacks)])
            queries = queries[:MAX_QUERIES]
            logger.info(f"[CodeXAgent] Queries ({len(queries)}): {queries}")

            # ── 4b: Parallel Search ───────────────────────────
            workers = [
                LlmAgent(
                    name=f"code_search_worker_{i}",
                    model=SEARCH_MODEL,
                    tools=[google_search],
                    instruction=_make_instruction(search_worker_prompt(q)),
                    include_contents="none",
                    output_key=f"code:result:{i}",
                )
                for i, q in enumerate(queries)
            ]
            parallel = ParallelAgent(name="code_parallel_search", sub_agents=workers)
            logger.info(f"[CodeXAgent] Running {len(workers)} parallel searches.")
            async for _ in parallel.run_async(ctx):
                pass

            results: List[str] = []
            for i, q in enumerate(queries):
                text = ctx.session.state.get(f"code:result:{i}", "").strip()
                if text:
                    results.append(f"[Search {i+1}: {q}]\n{text}")
            logger.info(f"[CodeXAgent] {len(results)} search results collected.")

            search_block = "\n\n".join(results) if results else "No search results available."

            # ── 4c: Fix Writer ────────────────────────────────
            final_output = await self._llm(
                ctx, "code_fix_writer",
                fix_writer_prompt(request, context_block, search_block, current_datetime),
                model=SEARCH_MODEL,
            )
            if not final_output:
                final_output = "Analysis complete. No output was generated."
                logger.warning("[CodeXAgent] Fix writer produced no output.")

        # ═════════════════════════════════════════════════════
        # WRITE PATH
        # ═════════════════════════════════════════════════════
        else:
            # ── 4a: KB Classifier ─────────────────────────────
            available_kbs = ", ".join(sorted(KB_FILES.keys()))
            raw_kb = await self._llm(
                ctx, "code_kb_classifier",
                kb_classifier_prompt(request, available_kbs),
            )
            kb_tokens = _parse_json_list(raw_kb)
            logger.info(f"[CodeXAgent] KB tokens: {kb_tokens}")

            # ── 4b: Load KB ───────────────────────────────────
            kb_block  = _load_kb(kb_tokens)
            kb_section = (
                "━━━ KNOWLEDGE BASE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Use these knowledge bases as your PRIMARY reference.\n\n"
                + kb_block
                + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                if kb_block else
                "No specific KB loaded. Use training knowledge for best output.\n"
            )

            # ── 4c: Task Planner ──────────────────────────────
            raw_manifest = await self._llm(
                ctx, "code_planner",
                task_planner_prompt(request, kb_section, context_block),
            )
            file_manifest = _parse_file_manifest(raw_manifest)
            logger.info(f"[CodeXAgent] Manifest: {len(file_manifest)} file(s)")
            for i, f in enumerate(file_manifest):
                logger.info(f"  [{i}] {f['path']} — {f['description']}")

            if not file_manifest:
                logger.warning("[CodeXAgent] Empty manifest — falling back.")
                file_manifest = [{"path": "output.py", "description": request[:80]}]

            # ── 4d: File Writer — one per file ────────────────
            manifest_summary = "\n".join(
                f"  {i+1}. {f['path']} — {f['description']}"
                for i, f in enumerate(file_manifest)
            )
            all_written: List[dict] = []

            for idx, finfo in enumerate(file_manifest):
                fpath = finfo["path"]
                fdesc = finfo["description"]
                logger.info(f"[CodeXAgent] Writing [{idx+1}/{len(file_manifest)}]: {fpath}")

                already_written = ""
                if all_written:
                    already_written = "\n━━━ ALREADY WRITTEN (reference) ━━━━━━━━━━━━━━━━\n"
                    for wf in all_written:
                        preview = wf["content"][:3000]
                        trunc   = " ...(truncated)" if len(wf["content"]) > 3000 else ""
                        already_written += f"\n### {wf['path']}\n```\n{preview}{trunc}\n```\n"
                    already_written += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

                content = await self._llm(
                    ctx, f"code_writer_{idx}",
                    file_writer_prompt(
                        request, fpath, fdesc,
                        kb_section, context_block,
                        manifest_summary, already_written,
                    ),
                )
                if content:
                    all_written.append({"path": fpath, "content": content})
                    logger.info(f"[CodeXAgent] Written: {fpath} ({len(content)} chars)")
                else:
                    logger.warning(f"[CodeXAgent] No output for: {fpath}")

            if not all_written:
                final_output = "Code generation failed. No files were produced."
                logger.warning("[CodeXAgent] No files written.")
            else:
                final_output = "\n\n".join(f["content"] for f in all_written)

        # ── STEP 5: Action Plan ───────────────────────────────
        action_plan = await self._llm(
            ctx, "code_action_plan",
            action_plan_prompt(final_output),
            output_key=KEY_ACTION_PLAN,
        )
        if not action_plan:
            action_plan = ctx.session.state.get(KEY_ACTION_PLAN, "")

        full_output = final_output.rstrip() + "\n\n---\n\n" + action_plan.strip()

        logger.info(
            f"[CodeXAgent] Done. mode={mode} output={len(final_output)}ch "
            f"plan={len(action_plan)}ch"
        )

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=full_output)],
            ),
            actions=EventActions(state_delta={KEY_ACTION_PLAN: action_plan}),
        )


# ─────────────────────────────────────────────────────────────
# EXPORTS
# ─────────────────────────────────────────────────────────────
codex_agent = CodeXAgent()

app = App(
    name="code_app",
    root_agent=codex_agent,
)

__all__ = ["codex_agent", "app", "CONTEXT_REQUEST_PREFIX"]
