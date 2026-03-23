# code.py
# ─────────────────────────────────────────────────────────────
# Code Agent Module (ADK Native Workflow)
#
# Flow:
#   1. Extract coding request from user content
#      • Sanitise stale preamble from multi-turn conversations
#      • Detect "## PROVIDED CONTEXT" split (second call with files)
#   2. Context Classifier LLM
#      • Does this request need EXISTING files on disk?
#      • YES only for explicit evidence of existing files.
#        A project NAME is never evidence — scratch projects always NO.
#      • If YES → yield ##CONTEXT_REQUEST## → STOP.
#        Root agent fetches files via file_system_mcp, re-calls.
#      • If NO  → proceed to Step 3.
#   3. KB Classifier LLM
#      • Decide which knowledge-base .md files are relevant.
#   4. Load KB files from disk (Python — no LLM).
#   5. Task Planner LLM
#      • Ordered FILE MANIFEST — every file to create or modify.
#   6. File Writer LLM — one call per file, never truncated.
#   7. Action Plan LLM
#      • Numbered steps for root agent: mkdir → write_file → setup.
#   8. Yield all files + action plan.
#
# ── IMPORTANT — ADK template engine ─────────────────────────
#   ADK's inject_session_state() scans every LlmAgent instruction
#   STRING for {variable} patterns and crashes on any {word} that
#   is a valid Python identifier. KB markdown, user code, and
#   project files are full of these. Doubling braces {{ }} does NOT
#   help — ADK strips all leading/trailing braces before the check.
#   ONLY FIX: callable instructions via _make_instruction().
#   See: google/adk/agents/llm_agent.py :: canonical_instruction()
# ─────────────────────────────────────────────────────────────

import os
import json
import logging
import datetime
import re
from pathlib import Path
from typing import AsyncGenerator, List

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.events import Event, EventActions
from google.adk.apps import App
from google.genai import types

from .config import config

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

logger = logging.getLogger("code_agent")
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
CODE_MODEL = config.CODE_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# ─────────────────────────────────────────────────────────────
# KNOWLEDGE BASE
# Dynamically discovered at startup — drop any .md file into
# the Knowledge-Base directory and it is picked up automatically.
# ─────────────────────────────────────────────────────────────
_KB_DIR: Path = Path(config.KNOWLEDGE_BASE)

KB_FILES: dict[str, str] = {
    p.stem.lower(): p.name
    for p in sorted(_KB_DIR.glob("*.md"))
    if p.is_file()
}

if KB_FILES:
    logger.info(
        f"Knowledge bases loaded ({len(KB_FILES)}): {', '.join(sorted(KB_FILES))}"
    )
else:
    logger.warning(f"No knowledge base files found in: {_KB_DIR}")

# ─────────────────────────────────────────────────────────────
# STATE KEYS
# ─────────────────────────────────────────────────────────────
KEY_USER_REQUEST    = "code:user_request"
KEY_PROJECT_CONTEXT = "code:project_context"
KEY_KB_TOKENS       = "code:kb_tokens"
KEY_FILE_MANIFEST   = "code:file_manifest"
KEY_FINAL_CODE      = "code:final_code"
KEY_ACTION_PLAN     = "code:action_plan"

# Sentinel that root agent detects to trigger file fetching
CONTEXT_REQUEST_PREFIX = "##CONTEXT_REQUEST##"

# ─────────────────────────────────────────────────────────────
# PREAMBLE NOISE PATTERNS
# Paragraphs whose first line matches one of these are stripped
# from the request before the classifier sees it. This prevents
# stale conversation turns (e.g. "show me my directory tree")
# from polluting the actual coding request.
# ─────────────────────────────────────────────────────────────
_NOISE_PATTERNS: List[str] = [
    r"(?i)^show\s+me\s+(my\s+)?director",
    r"(?i)^list\s+(the\s+)?files",
    r"(?i)^(hello|hi|hey)\b",
    r"(?i)^what\s+(is|are)\b",
    r"(?i)^i\s+have\s+shared",
    r"(?i)^okay,?\s+i\s+(will|see|am)",
    r"(?i)^executing\s+step",
]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _make_instruction(text: str):
    """
    Wrap a pre-built string in a callable so ADK sets
    bypass_state_injection = True and NEVER runs inject_session_state().
    This is the only reliable way to prevent crashes on curly-brace
    characters inside KB markdown, user code, and project files.
    """
    def _fn(_ctx: ReadonlyContext) -> str:
        return text
    return _fn


def _sanitise_request(raw: str) -> str:
    """
    Strip non-coding preamble paragraphs from a multi-turn conversation
    message. Returns the first paragraph that looks like a real coding
    request, plus everything after it.

    Example: if raw contains "show me my directory tree\n\nCreate a
    FastAPI project..." — returns only the FastAPI paragraph onward.
    """
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        return raw

    coding_start = len(paragraphs) - 1  # default: last paragraph
    for i, para in enumerate(paragraphs):
        first_line = para.splitlines()[0].strip()
        is_noise = any(re.match(pat, first_line) for pat in _NOISE_PATTERNS)
        if not is_noise:
            coding_start = i
            break

    if coding_start == 0:
        return raw  # nothing to strip

    cleaned = "\n\n".join(paragraphs[coding_start:])
    logger.info(
        f"[CodeAgent] Sanitiser stripped {coding_start} preamble paragraph(s). "
        f"Request: {len(raw)} → {len(cleaned)} chars."
    )
    return cleaned


def _load_kb(tokens: List[str]) -> str:
    """
    Load and concatenate markdown files for the given KB token list.
    Returns a single raw string. Braces NOT escaped — caller uses
    _make_instruction() to bypass ADK's template scanner.
    """
    sections: List[str] = []
    for token in tokens:
        filename = KB_FILES.get(token.lower())
        if not filename:
            logger.debug(f"[CodeAgent] No KB file for token '{token}' — skipping.")
            continue
        filepath = _KB_DIR / filename
        if not filepath.exists():
            logger.warning(f"[CodeAgent] KB file not found: {filepath}")
            continue
        content = filepath.read_text(encoding="utf-8")
        sections.append(
            f"### [{token.upper()} KNOWLEDGE BASE — {filename}]\n\n{content}"
        )
        logger.info(f"[CodeAgent] Loaded KB: {filename} ({len(content)} chars)")

    if not sections:
        return ""
    return "\n\n" + ("─" * 60 + "\n\n").join(sections)


def _parse_json_list(raw: str) -> List[str]:
    """Parse LLM response into a list of strings. JSON array or fallback."""
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
    """
    Parse Task Planner output into file descriptors.
    Expected: "1. path/to/file.py — Description"
    Returns:  [{"path": "...", "description": "..."}, ...]
    """
    files = []
    for line in raw.strip().splitlines():
        line = line.strip()
        match = re.match(r"^(?:\d+[\.\)]|-)\s+(\S+)\s+[—–-]+\s+(.+)$", line)
        if match:
            files.append({
                "path":        match.group(1).strip(),
                "description": match.group(2).strip(),
            })
    return files


# ─────────────────────────────────────────────────────────────
# HELPER — extract file contents from session events
#
# When root agent reads files via file_system_mcp and then calls
# code_agent, the file contents live in the session event stream
# as function_response parts — NOT in user_content. This helper
# scans all session events and assembles a ## PROVIDED CONTEXT block
# so CodeAgent is never dependent on root agent assembling the
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
            if not any(k in tool_name.lower() for k in ("read", "list", "get")):
                continue
            response = getattr(fr, "response", None)
            if not response:
                continue

            text_content = ""
            file_path = tool_name

            if isinstance(response, dict):
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
# CODE AGENT
# ─────────────────────────────────────────────────────────────

class CodeAgent(BaseAgent):
    """
    Full-spectrum code writing agent.

    Capabilities:
    • Any language: Python, Go, JS/TS, Bash, Java, C++, Rust, SQL, ...
    • Web backends: Flask, FastAPI, Django, Node.js (TypeScript)
    • Web frontend: React.js (TypeScript) with Vite, Zustand, Tailwind
    • Full-stack: any backend + React, auth, RBAC, Docker, Nginx
    • Databases: MySQL, PostgreSQL, SQLite, MongoDB, Redis
    • Complexity: beginner scripts → production full-stack projects
    • Modes: write from scratch / extend / modify / refactor / fix

    Requests root agent to fetch existing project files when needed
    (via file_system_mcp). Returns written files + an ACTION PLAN for
    root agent to execute using file_system_mcp (mkdir + write_file).
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="code_agent",
            description=(
                "Writes complete, production-quality code from beginner scripts to "
                "full-stack web applications. Supports Python, Go, JavaScript, TypeScript, "
                "Bash, Java, C++, Rust, SQL/NoSQL. Handles Flask, FastAPI, Django, Node.js "
                "backends and React.js (TypeScript) frontends. Can work from scratch or on "
                "existing projects. Uses an internal knowledge base and requests project "
                "files from root agent when needed. Returns an action plan for root agent "
                "to write all files to disk via file_system_mcp."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info("[CodeAgent] Pipeline started.")

        # ── STEP 0: Clear stale state from any previous task ─────
        for key in (
            KEY_USER_REQUEST, KEY_PROJECT_CONTEXT,
            KEY_KB_TOKENS, KEY_FILE_MANIFEST,
            KEY_FINAL_CODE, KEY_ACTION_PLAN,
        ):
            ctx.session.state.pop(key, None)
        logger.info("[CodeAgent] State cleared — starting fresh.")

        # ── STEP 1: Extract request + detect provided context ──
        #
        # Three cases handled here:
        #
        # Case A — First call, no prior CONTEXT_REQUEST:
        #   user_content = full coding request. Parse normally.
        #
        # Case B — Root agent assembled context correctly (ideal):
        #   user_content = "<request>\n## PROVIDED CONTEXT\n<files>"
        #
        # Case C — Root agent passed only its short instruction after
        #   CONTEXT_REQUEST (the common failure mode):
        #   Detect by scanning session events for our own prior
        #   ##CONTEXT_REQUEST## response — extract the preserved
        #   request text from that event + file contents from
        #   file_system_mcp function_response events that followed.

        raw_input = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    raw_input += part.text

        # Detect whether WE already sent a CONTEXT_REQUEST this session
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

        context_request_sent = bool(prior_context_request_text)

        user_request    = raw_input
        project_context = ""

        if "## PROVIDED CONTEXT" in raw_input:
            # Case B — root agent assembled it correctly
            parts_split     = raw_input.split("## PROVIDED CONTEXT", 1)
            user_request    = parts_split[0].strip()
            project_context = "## PROVIDED CONTEXT\n" + parts_split[1].strip()
            logger.info(
                f"[CodeAgent] Project context found in user_content "
                f"({len(project_context)} chars)."
            )

        elif context_request_sent:
            # Case C — recover request from the preserved text at the bottom
            # of the CONTEXT_REQUEST event
            if "Original request preserved for re-submission:" in prior_context_request_text:
                user_request = prior_context_request_text.split(
                    "Original request preserved for re-submission:", 1
                )[1].strip()
            else:
                user_request = raw_input

            logger.info(
                f"[CodeAgent] Request recovered from prior CONTEXT_REQUEST event "
                f"({len(user_request)} chars). user_content was: '{raw_input[:80]}'"
            )

            project_context = _extract_context_from_session(ctx)
            if project_context:
                logger.info(
                    f"[CodeAgent] Context extracted from session events "
                    f"({len(project_context)} chars)."
                )
            else:
                logger.warning(
                    "[CodeAgent] Could not extract context from session events — "
                    "proceeding without project files."
                )

        else:
            # Case A — first call, no prior CONTEXT_REQUEST
            if not raw_input:
                logger.warning("[CodeAgent] No request found.")
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="Error: No coding request was provided.")],
                    ),
                )
                return

        # ── Sanitise stale preamble ───────────────────────────
        if not project_context:
            user_request = _sanitise_request(user_request)

        logger.info(
            f"[CodeAgent] Request ({len(user_request)} chars): "
            f"'{user_request[:120]}{'...' if len(user_request) > 120 else ''}'"
        )
        logger.info(
            f"[CodeAgent] Project context: "
            f"{'present (' + str(len(project_context)) + ' chars)' if project_context else 'none'}"
        )

        # ── STEP 2: Context Classifier ────────────────────────
        # Decides whether EXISTING files on disk must be read first.
        # Skip entirely if context was already provided on this call,
        # OR if a CONTEXT_REQUEST was already sent (prevents infinite loop
        # when session-event extraction partially fails).
        #
        # ⚠ KEY RULE — what qualifies as YES:
        #   YES requires EXPLICIT evidence that specific source files
        #   already exist and need to be read. A project NAME is NOT
        #   evidence — "Sameer Cars" is just a name for a new project.
        #   Scratch projects are ALWAYS NO regardless of their name.
        if not project_context and not context_request_sent:
            logger.info("[CodeAgent] Running context classifier.")

            classifier_prompt = (
                "You are a project context triage assistant for a code writing agent.\n\n"
                "Coding request:\n"
                + user_request + "\n\n"
                "Decide: does completing this request require reading files that ALREADY "
                "EXIST on disk before any code can be written?\n\n"
                "Answer NEEDS_CONTEXT: YES ONLY when the request contains EXPLICIT evidence "
                "that source files already exist and must be read first:\n"
                "- The user pastes actual existing code inline\n"
                "- The user names a specific file path that already exists\n"
                "- The user says 'my existing code', 'this function I have', "
                "'the current file', 'update this class', 'add to this module'\n"
                "- A traceback references a specific file that needs to be read\n"
                "- The user says 'my existing project' AND names specific files or modules\n\n"
                "Answer NEEDS_CONTEXT: NO for ALL of the following:\n"
                "- Building a NEW project from scratch — ANY project name is fine, "
                "it is just a label, not evidence of existing files\n"
                "- Creating a new app, API, backend, frontend, or service\n"
                "- Writing a standalone script, utility, query, or config file\n"
                "- Requests containing 'create', 'build', 'generate', 'scaffold', "
                "'write a new', 'new project', 'develop', 'design'\n"
                "- Technology stack mentioned but NO existing code shown\n\n"
                "CRITICAL EXAMPLES:\n"
                "  'Create a FastAPI backend for Sameer Cars' → NEEDS_CONTEXT: NO\n"
                "  'Build a new React app called TaskMaster' → NEEDS_CONTEXT: NO\n"
                "  'Write a Python script to parse CSV files' → NEEDS_CONTEXT: NO\n"
                "  'Add a password reset endpoint to my existing Flask app' → NEEDS_CONTEXT: YES\n"
                "  'Fix the bug in routes/users.py line 42' → NEEDS_CONTEXT: YES\n\n"
                "Your response MUST start with exactly one of these two lines:\n"
                "NEEDS_CONTEXT: YES\n"
                "NEEDS_CONTEXT: NO\n\n"
                "If YES, follow immediately with:\n"
                "FILES_NEEDED:\n"
                "- exact/path/to/file.py\n"
                "- directory listing of: src/\n"
            )

            ctx_classifier = LlmAgent(
                name="code_context_classifier",
                model=CODE_MODEL,
                instruction=_make_instruction(classifier_prompt),
                include_contents="none",
            )

            classifier_output = ""
            async for event in ctx_classifier.run_async(ctx):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            classifier_output += part.text

            logger.debug(f"[CodeAgent] Context classifier:\n{classifier_output}")

            # Check ONLY the first non-empty line of the response.
            # Prevents false positives from any explanatory text the
            # LLM appends after the decision line.
            first_decision_line = next(
                (ln.strip() for ln in classifier_output.splitlines() if ln.strip()),
                ""
            ).upper()
            needs_context = first_decision_line.startswith("NEEDS_CONTEXT: YES")

            logger.info(
                f"[CodeAgent] Context classifier decision: "
                f"{'YES — requesting files' if needs_context else 'NO — proceeding'}"
            )

            if needs_context:
                files_section = ""
                if "FILES_NEEDED:" in classifier_output:
                    files_section = classifier_output.split("FILES_NEEDED:", 1)[1].strip()

                logger.info("[CodeAgent] Yielding CONTEXT_REQUEST.")

                context_request_body = (
                    CONTEXT_REQUEST_PREFIX + "\n\n"
                    "Before I can write the code accurately, I need to read the following "
                    "existing files and/or directories from the project.\n\n"
                    "**Please use file_system_mcp to fetch each item listed below, then "
                    "call me again with the original request followed by:**\n\n"
                    "```\n"
                    "## PROVIDED CONTEXT\n"
                    "<paste each file's full content here, labelled with its path>\n"
                    "```\n\n"
                    "**Files / directories needed:**\n"
                    + files_section + "\n\n"
                    "---\n"
                    "_Original request preserved for re-submission:_\n\n"
                    + user_request
                )

                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=context_request_body)],
                    ),
                )
                return  # Stop — root agent will re-invoke with context

        else:
            if project_context:
                logger.info("[CodeAgent] Context already provided — skipping classifier.")
            else:
                logger.info("[CodeAgent] Prior CONTEXT_REQUEST sent — skipping classifier, proceeding with available data.")

        # ── STEP 3: KB Classifier ─────────────────────────────
        available_kbs = ", ".join(sorted(KB_FILES.keys()))

        kb_classifier_prompt = (
            "You are a Knowledge Base Classifier for a Code Writing Agent.\n\n"
            "Available knowledge bases:\n"
            + available_kbs + "\n\n"
            "Coding request:\n"
            + user_request + "\n\n"
            "Return ONLY the KB keys directly relevant to this request.\n\n"
            "Selection guide:\n"
            "- 'python'            → any Python script, utility, or backend logic\n"
            "- 'backend_flask'     → Flask web application or REST API\n"
            "- 'backend_fastapi'   → FastAPI web application or REST API\n"
            "- 'backend_django'    → Django web application or REST API\n"
            "- 'backend_nodejs'    → Node.js / Express (TypeScript) backend\n"
            "- 'frontend_reactjs'  → React.js (TypeScript) frontend / UI components\n"
            "- 'fullstack'         → full-stack integration, auth, RBAC, Docker, Nginx\n"
            "- 'mysql'             → MySQL queries, schema, ORM models\n"
            "- 'psql'              → PostgreSQL queries, schema, ORM models\n"
            "- 'sqlite'            → SQLite queries, schema\n"
            "- 'mongodb'           → MongoDB queries, aggregation, ODM models\n\n"
            "Rules:\n"
            "- Return a valid JSON array, e.g.: [\"backend_fastapi\", \"psql\"]\n"
            "- Include ALL relevant KBs — Flask+MySQL → include both.\n"
            "- Full-stack → include 'fullstack' + specific backend + 'frontend_reactjs'.\n"
            "- If no KB matches the language/framework, return [].\n"
            "- JSON array ONLY — no explanation, no markdown.\n"
        )

        kb_classifier = LlmAgent(
            name="kb_classifier_agent",
            model=CODE_MODEL,
            instruction=_make_instruction(kb_classifier_prompt),
            include_contents="none",
        )

        raw_kb_tokens = ""
        async for event in kb_classifier.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        raw_kb_tokens += part.text

        logger.debug(f"[CodeAgent] KB classifier raw output: {raw_kb_tokens!r}")

        kb_tokens = _parse_json_list(raw_kb_tokens)
        logger.info(f"[CodeAgent] KB tokens selected: {kb_tokens}")
        ctx.session.state[KEY_KB_TOKENS] = kb_tokens

        # ── STEP 4: Load KB files from disk ──────────────────
        kb_block = _load_kb(kb_tokens)

        kb_section = (
            "━━━ KNOWLEDGE BASE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Use the following knowledge bases as your PRIMARY reference.\n"
            "Follow their patterns, conventions, and best practices exactly.\n\n"
            + kb_block
            + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            if kb_block
            else (
                "No specific knowledge base was loaded. "
                "Use your training knowledge to write the best possible code.\n"
            )
        )

        logger.info(f"[CodeAgent] KB block: {len(kb_block)} chars")

        # Context section for injection into all downstream prompts
        context_section = (
            "\n━━━ PROJECT CONTEXT (EXISTING FILES) ━━━━━━━━━━━━━━━━━━━━━━\n"
            + project_context
            + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            if project_context
            else ""
        )

        # ── STEP 5: Task Planner — build FILE MANIFEST ────────
        planner_prompt = (
            "You are a Senior Software Architect and Project Planner.\n\n"
            + kb_section
            + context_section
            + "\n━━━ CODING REQUEST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + user_request
            + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Produce a complete ordered FILE MANIFEST of every file that must be "
            "CREATED or MODIFIED to fulfil this request.\n\n"
            "Rules:\n"
            "- Dependency order: config → models → services → routes → main → tests\n"
            "- Web projects must include: .env.example, requirements.txt or package.json, "
            "README.md with setup and API testing instructions\n"
            "- Full-stack: include both backend AND frontend file trees\n"
            "- Modifications: list only files that actually change\n"
            "- Be complete — no TODOs, no placeholder files\n\n"
            "PYTHON PROJECTS — setup.py (MANDATORY):\n"
            "For ANY Python project include 'setup.py' as the LAST manifest entry.\n"
            "It must: load BASE_DIR from .env (default '.'), create a venv with "
            "'py -3.11' (Windows) or 'python3.11' (Linux), and install requirements.txt.\n\n"
            "Output ONLY a numbered list in this EXACT format:\n"
            "1. relative/path/to/file.ext — One-line description\n"
            "2. another/file.py — One-line description\n"
        )

        planner = LlmAgent(
            name="code_planner_agent",
            model=CODE_MODEL,
            instruction=_make_instruction(planner_prompt),
            include_contents="none",
        )

        raw_manifest = ""
        async for event in planner.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        raw_manifest += part.text

        logger.debug(f"[CodeAgent] Raw manifest:\n{raw_manifest}")

        file_manifest = _parse_file_manifest(raw_manifest)
        logger.info(f"[CodeAgent] File manifest: {len(file_manifest)} file(s)")
        for i, f in enumerate(file_manifest):
            logger.info(f"  [{i}] {f['path']} — {f['description']}")

        ctx.session.state[KEY_FILE_MANIFEST] = json.dumps(file_manifest)

        if not file_manifest:
            logger.warning("[CodeAgent] Empty manifest — falling back to single-file mode.")
            file_manifest = [{"path": "output", "description": user_request[:80]}]

        # ── STEP 6: File Writer — one file at a time ──────────
        all_written_files: List[dict] = []

        manifest_summary = "\n".join(
            f"  {i+1}. {f['path']} — {f['description']}"
            for i, f in enumerate(file_manifest)
        )

        for idx, file_info in enumerate(file_manifest):
            file_path = file_info["path"]
            file_desc = file_info["description"]

            logger.info(
                f"[CodeAgent] Writing file {idx + 1}/{len(file_manifest)}: {file_path}"
            )

            already_written = ""
            if all_written_files:
                already_written = (
                    "\n━━━ ALREADY WRITTEN FILES (reference only) ━━━━━━━━━━━━━━\n"
                )
                for wf in all_written_files:
                    preview = wf["content"][:3000]
                    truncated = " ... (truncated)" if len(wf["content"]) > 3000 else ""
                    already_written += (
                        f"\n### {wf['path']}\n```\n{preview}{truncated}\n```\n"
                    )
                already_written += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            writer_prompt = (
                "You are an expert software engineer.\n\n"
                + kb_section
                + context_section
                + already_written
                + "\n━━━ FULL PROJECT MANIFEST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                + manifest_summary
                + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "━━━ ORIGINAL REQUEST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                + user_request
                + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "━━━ CURRENT FILE TO WRITE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Path:        " + file_path + "\n"
                "Description: " + file_desc + "\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Write the COMPLETE content of this ONE file.\n\n"
                "MANDATORY OUTPUT RULES:\n"
                "1. Output ONLY the file content — no explanation before or after.\n"
                "2. Start with the file header:\n"
                "   ### `" + file_path + "`\n"
                "   then immediately a code block with the correct language tag.\n"
                "3. NEVER truncate — output the COMPLETE file, first line to last.\n"
                "4. NEVER use '# ... rest of code', '// TODO', 'pass', or '...'.\n"
                "5. Language tags:\n"
                "   Python → ```python  |  TypeScript → ```typescript\n"
                "   JavaScript → ```javascript  |  Go → ```go\n"
                "   SQL → ```sql  |  Bash → ```bash  |  YAML → ```yaml\n"
                "   JSON → ```json  |  TOML → ```toml  |  .env → ```env\n"
                "   Dockerfile → ```dockerfile  |  Nginx → ```nginx\n"
                "6. Code quality:\n"
                "   - Full error handling, no bare except, no silent failures\n"
                "   - Type hints on all Python functions\n"
                "   - TypeScript strict mode — no 'any' types\n"
                "   - Docstrings on classes and public functions\n"
                "   - No hardcoded secrets — all credentials via .env\n"
                "   - Follow KB patterns exactly when a KB was loaded\n"
            )

            writer = LlmAgent(
                name=f"code_writer_{idx}",
                model=CODE_MODEL,
                instruction=_make_instruction(writer_prompt),
                include_contents="none",
            )

            file_content = ""
            async for event in writer.run_async(ctx):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            file_content += part.text

            if file_content:
                all_written_files.append({"path": file_path, "content": file_content})
                logger.info(f"[CodeAgent] Written: {file_path} ({len(file_content)} chars)")
            else:
                logger.warning(f"[CodeAgent] Writer produced no output for: {file_path}")

        # ── STEP 7: Action Plan ───────────────────────────────
        files_summary_for_plan = "\n".join(
            f"  {i+1}. {f['path']}" for i, f in enumerate(all_written_files)
        )

        action_plan_prompt = (
            "You are a deployment execution planner.\n\n"
            "Files written by code_agent:\n"
            + files_summary_for_plan + "\n\n"
            "Original request:\n"
            + user_request + "\n\n"
            "Produce a numbered ACTION PLAN for root agent to:\n"
            "1. Create all required directories\n"
            "2. Write every file to disk\n"
            "3. Run setup and start the project\n\n"
            "Root agent tools:\n"
            "  file_system_mcp — create_directory, write_file, read_file, "
            "list_directory, delete_file\n"
            "  solution_agent  — for any errors during execution\n\n"
            "Rules:\n"
            "- Phase 1: all create_directory steps first\n"
            "- Phase 2: all write_file steps (one per file)\n"
            "- Phase 3: setup and run commands\n"
            "  For Python projects: final command is 'py setup.py'\n"
            "  For Node projects:   final command is 'npm install && npm run dev'\n"
            "- Label every step: [file_system_mcp] or [shell_command]\n"
            "- End with: 'If any step fails, call solution_agent with the error.'\n\n"
            "## Action Plan\n\n"
            "### Phase 1 — Create Directories\n"
            "#### Step 1 — [file_system_mcp]\n"
            "**Operation:** create_directory\n"
            "**Path:** `path/to/dir`\n\n"
            "### Phase 2 — Write Files\n"
            "#### Step N — [file_system_mcp]\n"
            "**Operation:** write_file\n"
            "**Path:** `path/to/file.py`\n"
            "**Content:** _(output from code_agent — file N)_\n\n"
            "### Phase 3 — Setup & Run\n"
            "#### Step N — [shell_command]\n"
            "**Command:** `py setup.py`\n"
            "**Expected:** Setup complete.\n\n"
            "### If Errors Occur\n"
            "Call solution_agent with the full error message and stack trace.\n"
        )

        action_plan_agent = LlmAgent(
            name="code_action_plan_agent",
            model=CODE_MODEL,
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

        # ── STEP 8: Assemble final output ─────────────────────
        if not all_written_files:
            final_output = "Code generation failed. No files were produced."
            logger.warning("[CodeAgent] No files were written.")
        else:
            files_output = "\n\n".join(f["content"] for f in all_written_files)
            final_output = (
                files_output.rstrip()
                + "\n\n---\n\n"
                + action_plan.strip()
            )

        logger.info(
            f"[CodeAgent] Pipeline complete. "
            f"Files: {len(all_written_files)}. Output: {len(final_output)} chars."
        )

        ctx.session.state[KEY_FINAL_CODE] = final_output

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=final_output)],
            ),
            actions=EventActions(
                state_delta={
                    KEY_FINAL_CODE:  final_output,
                    KEY_ACTION_PLAN: action_plan,
                }
            ),
        )


# ─────────────────────────────────────────────────────────────
# EXPORTS
# ─────────────────────────────────────────────────────────────
code_agent = CodeAgent()

app = App(
    name="code_app",
    root_agent=code_agent,
)

__all__ = ["code_agent", "app", "CONTEXT_REQUEST_PREFIX"]
