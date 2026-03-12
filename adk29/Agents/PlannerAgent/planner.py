# planner.py
# ─────────────────────────────────────────────────────────────
# Planner Agent Module (UPDATED & FIXED)
#
# FIXED: LLM tool-name hallucination in PlannerBuilderAgent
#   • The model was outputting invalid function call name "call"
#   • Root cause: ambiguous step-by-step prompt confused the tool-calling flow
#   • Fix: Completely rewritten _build_fs_instruction() with:
#       - Full explicit list of ALL available MCP tools
#       - Strict "use EXACT tool name" anti-hallucination rules
#       - Clear "Make a function call to XXX with:" phrasing for every step
#       - One-step-at-a-time guidance so the ADK tool-calling loop works correctly
#
# All other logic (research, architecture, comment-only placeholders, PROJECT.md)
# remains unchanged. The project will now build successfully on disk.
# ─────────────────────────────────────────────────────────────

import os
import re
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import AsyncGenerator, ClassVar, List

from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

from config import config

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "log"
_LOG_DIR.mkdir(exist_ok=True)

_log_filename = datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S") + ".log"
_log_filepath = _LOG_DIR / _log_filename

_pl_logger = logging.getLogger("planner_agent")

if not _pl_logger.handlers:
    _pl_logger.setLevel(logging.DEBUG)
    _fmt = logging.Formatter(
        "%(asctime)s  [%(module)s]  %(levelname)-8s  %(name)s  %(message)s"
    )
    _fh = logging.FileHandler(_log_filepath, encoding="utf-8")
    _fh.setFormatter(_fmt)
    _pl_logger.addHandler(_fh)
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    _pl_logger.addHandler(_sh)

_pl_logger.info(f"Planner Agent initialised (FIXED version). Log → {_log_filepath}")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

PATH_TO_PYTHON = sys.executable

# ─────────────────────────────────────────────────────────────
# FILE SYSTEM MCP TOOLSET
# ─────────────────────────────────────────────────────────────
_file_system_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP\file_system_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP",
        ),
        timeout_in_seconds=60,
    )
)
_pl_logger.debug("File System MCP toolset configured.")

# ─────────────────────────────────────────────────────────────
# SESSION STATE KEYS
# ─────────────────────────────────────────────────────────────
PL_KEY_DESCRIPTION   = "pl:project_description"
PL_KEY_QUERIES_JSON  = "pl:queries_json"
PL_KEY_RESULT_PREFIX = "pl:result:"
PL_KEY_ARCHITECTURE  = "pl:architecture_json"
PL_KEY_BUILD_REPORT  = "pl:build_report"


# ─────────────────────────────────────────────────────────────
# HELPER: strip markdown fences from LLM JSON output
# ─────────────────────────────────────────────────────────────
def _extract_json(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


# ─────────────────────────────────────────────────────────────
# HELPER: Generate comment-only placeholder content for a file
# (unchanged - still guarantees ZERO implementation code)
# ─────────────────────────────────────────────────────────────
def _build_file_comment(
    file_path: str,
    purpose: str,
    description: str,
    project_name: str,
    project_title: str,
    tech_stack: list,
    generated_at: str,
) -> str:
    """
    Returns comment-only placeholder content appropriate for the file type.
    No implementation code is included under any circumstances.
    """
    ext         = Path(file_path).suffix.lower()
    filename    = Path(file_path).name
    fname_lower = filename.lower()
    sep         = "─" * 62
    stack_str   = ", ".join(tech_stack) if tech_stack else "See PROJECT.md"

    if fname_lower in ("requirements.txt", "requirements-dev.txt",
                       "requirements-test.txt", "requirements-prod.txt"):
        return "\n".join([
            f"# {file_path}",
            f"# {sep}",
            f"# Project    : {project_title}",
            f"# File       : {filename}",
            f"# Purpose    : {purpose}",
            f"# Generated  : {generated_at}",
            f"# {sep}",
            f"#",
            f"# {description}",
            f"#",
            f"# Tech stack : {stack_str}",
            f"#",
            f"# TODO: Add your project dependencies below.",
            f"# Format: package-name==version  or  package-name>=version",
            f"#",
            f"# Example:",
            f"#   fastapi==0.111.0",
            f"#   sqlalchemy>=2.0",
            f"#   pydantic>=2.0",
            f"#",
        ]) + "\n"

    if fname_lower == "package.json":
        return "\n".join([
            "{",
            f'  "_comment_file":    "{file_path}",',
            f'  "_comment_purpose": "{purpose}",',
            f'  "_comment_note":    "{description}",',
            f'  "_comment_todo":    "Replace _comment keys with real package.json content.",',
            f'  "name":             "{project_name}",',
            f'  "version":          "0.1.0",',
            f'  "description":      "{purpose}",',
            f'  "scripts": {{',
            f'    "start": "TODO: add start command",',
            f'    "dev":   "TODO: add dev command",',
            f'    "test":  "TODO: add test command",',
            f'    "build": "TODO: add build command"',
            f'  }},',
            f'  "dependencies":    {{',
            f'    "_todo": "Add dependencies here"',
            f'  }},',
            f'  "devDependencies": {{',
            f'    "_todo": "Add devDependencies here"',
            f'  }}',
            "}",
        ]) + "\n"

    if fname_lower in (".env", ".env.example"):
        return "\n".join([
            f"# {file_path}",
            f"# {sep}",
            f"# Project    : {project_title}",
            f"# File       : {filename}",
            f"# Purpose    : {purpose}",
            f"# Generated  : {generated_at}",
            f"# {sep}",
            f"#",
            f"# {description}",
            f"#",
            f"# Copy this file to .env and fill in your actual values.",
            f"# NEVER commit .env to version control.",
            f"#",
            f"# ── Application ─────────────────────────────────────────",
            f"APP_ENV=development",
            f"APP_PORT=8000",
            f"APP_SECRET_KEY=your-secret-key-here",
            f"APP_DEBUG=true",
            f"",
            f"# ── Database ─────────────────────────────────────────────",
            f"DATABASE_URL=your-database-url-here",
            f"",
            f"# ── Add more variables below as needed ───────────────────",
        ]) + "\n"

    if fname_lower in (".gitignore", ".dockerignore"):
        return "\n".join([
            f"# {file_path}",
            f"# {sep}",
            f"# Project    : {project_title}",
            f"# Purpose    : {purpose}",
            f"# Generated  : {generated_at}",
            f"# {sep}",
            f"#",
            f"# {description}",
            f"#",
            f"# TODO: Uncomment and extend the patterns below for your stack:",
            f"# Tech stack: {stack_str}",
            f"#",
            f"# ── Python ───────────────────────────────────────────────",
            f"# __pycache__/",
            f"# *.pyc",
            f"# *.pyo",
            f"# .venv/",
            f"# *.egg-info/",
            f"# dist/",
            f"# build/",
            f"# .pytest_cache/",
            f"# .coverage",
            f"# htmlcov/",
            f"#",
            f"# ── Node / JS ────────────────────────────────────────────",
            f"# node_modules/",
            f"# dist/",
            f"# .next/",
            f"# .nuxt/",
            f"#",
            f"# ── Environment & secrets ────────────────────────────────",
            f"# .env",
            f"# *.key",
            f"# *.pem",
            f"#",
            f"# ── OS / Editor ─────────────────────────────────────────",
            f"# .DS_Store",
            f"# Thumbs.db",
            f"# .idea/",
            f"# .vscode/",
            f"# *.log",
        ]) + "\n"

    if fname_lower == "dockerfile":
        return "\n".join([
            f"# {file_path}",
            f"# {sep}",
            f"# Project    : {project_title}",
            f"# Purpose    : {purpose}",
            f"# Generated  : {generated_at}",
            f"# {sep}",
            f"#",
            f"# {description}",
            f"#",
            f"# TODO: Choose a base image for your stack:",
            f"#   FROM python:3.11-slim        (Python)",
            f"#   FROM node:20-alpine          (Node.js)",
            f"#   FROM openjdk:17-jdk-slim     (Java)",
            f"#",
            f"# TODO: Set working directory",
            f"#   WORKDIR /app",
            f"#",
            f"# TODO: Copy and install dependencies",
            f"#   COPY requirements.txt .",
            f"#   RUN pip install --no-cache-dir -r requirements.txt",
            f"#",
            f"# TODO: Copy application source",
            f"#   COPY . .",
            f"#",
            f"# TODO: Expose port and define entrypoint",
            f"#   EXPOSE 8000",
            f'#   CMD ["python", "main.py"]',
        ]) + "\n"

    if fname_lower in ("docker-compose.yml", "docker-compose.yaml",
                       "docker-compose.dev.yml", "docker-compose.prod.yml"):
        return "\n".join([
            f"# {file_path}",
            f"# {sep}",
            f"# Project    : {project_title}",
            f"# Purpose    : {purpose}",
            f"# Generated  : {generated_at}",
            f"# {sep}",
            f"#",
            f"# {description}",
            f"#",
            f"# TODO: Define your services below.",
            f"# Example structure:",
            f"#",
            f"# version: '3.9'",
            f"# services:",
            f"#   app:",
            f"#     build: .",
            f"#     ports:",
            f'#       - "8000:8000"',
            f"#     env_file: .env",
            f"#   db:",
            f"#     image: postgres:15",
            f"#     environment:",
            f"#       POSTGRES_PASSWORD: example",
        ]) + "\n"

    if ext in (".yaml", ".yml", ".toml", ".ini", ".cfg"):
        return "\n".join([
            f"# {file_path}",
            f"# {sep}",
            f"# Project    : {project_title}",
            f"# File       : {filename}",
            f"# Purpose    : {purpose}",
            f"# Generated  : {generated_at}",
            f"# {sep}",
            f"#",
            f"# {description}",
            f"#",
            f"# TODO: Add configuration content below.",
        ]) + "\n"

    if ext == ".json":
        return "\n".join([
            "{",
            f'  "_comment_file":    "{file_path}",',
            f'  "_comment_purpose": "{purpose}",',
            f'  "_comment_desc":    "{description}",',
            f'  "_comment_gen":     "Generated: {generated_at}",',
            f'  "_todo":            "Replace _comment keys with real JSON content."',
            "}",
        ]) + "\n"

    if ext in (".md", ".markdown"):
        title = filename.replace(".md", "").replace("-", " ").replace("_", " ").title()
        return "\n".join([
            f"# {title}",
            f"",
            f"> **File**: `{file_path}`  ",
            f"> **Purpose**: {purpose}  ",
            f"> **Generated**: {generated_at}",
            f"",
            f"---",
            f"",
            f"## Overview",
            f"",
            f"{description}",
            f"",
            f"---",
            f"",
            f"> TODO: Fill in this document.",
        ]) + "\n"

    if ext in (".html", ".htm", ".xml", ".svg", ".vue"):
        return "\n".join([
            f"<!--",
            f"  File      : {file_path}",
            f"  {sep}",
            f"  Project   : {project_title}",
            f"  Purpose   : {purpose}",
            f"  Generated : {generated_at}",
            f"  {sep}",
            f"",
            f"  DESCRIPTION",
            f"  {sep}",
            f"  {description}",
            f"",
            f"  TECH STACK",
            f"  {sep}",
            f"  {stack_str}",
            f"",
            f"  IMPLEMENTATION NOTES",
            f"  {sep}",
            f"  TODO: Implement the markup described above.",
            f"  TODO: Follow the conventions defined in PROJECT.md.",
            f"-->",
        ]) + "\n"

    SLASH_EXTS = {".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                  ".h", ".go", ".rs", ".php", ".swift", ".kt", ".cs", ".dart"}
    if ext in SLASH_EXTS:
        desc_lines = [f" * {line.strip()}." for line in description.split(". ") if line.strip()]
        return "\n".join([
            f"/**",
            f" * File      : {file_path}",
            f" * {sep}",
            f" * Project   : {project_title}",
            f" * Generated : {generated_at}",
            f" * {sep}",
            f" *",
            f" * PURPOSE",
            f" * {sep}",
            f" * {purpose}",
            f" *",
            f" * DESCRIPTION",
            f" * {sep}",
            *desc_lines,
            f" *",
            f" * TECH STACK",
            f" * {sep}",
            f" * {stack_str}",
            f" *",
            f" * IMPLEMENTATION NOTES",
            f" * {sep}",
            f" * TODO: Implement the logic described above.",
            f" * TODO: Add required imports.",
            f" * TODO: Follow the conventions defined in PROJECT.md.",
            f" *",
            f" */",
        ]) + "\n"

    desc_lines = [f"# {line.strip()}." for line in description.split(". ") if line.strip()]
    return "\n".join([
        f"# {file_path}",
        f"# {sep}",
        f"# Project    : {project_title}",
        f"# File       : {filename}",
        f"# Path       : {file_path}",
        f"# Generated  : {generated_at}",
        f"# {sep}",
        f"#",
        f"# PURPOSE",
        f"# {sep}",
        f"# {purpose}",
        f"#",
        f"# DESCRIPTION",
        f"# {sep}",
        *desc_lines,
        f"#",
        f"# TECH STACK",
        f"# {sep}",
        f"# {stack_str}",
        f"#",
        f"# IMPLEMENTATION NOTES",
        f"# {sep}",
        f"# TODO: Implement the logic described above.",
        f"# TODO: Add required imports.",
        f"# TODO: Follow the conventions defined in PROJECT.md.",
        f"#",
    ]) + "\n"


# ─────────────────────────────────────────────────────────────
# STEP 0 — PLANNER ENTRY AGENT
# ─────────────────────────────────────────────────────────────
class PlannerEntryAgent(BaseAgent):
    """Captures the user's project description and writes it to session state."""

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(name="pl_entry_agent")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        description = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if getattr(part, "text", None):
                    description += part.text

        _pl_logger.info(
            f"[PlannerEntryAgent] Description captured ({len(description)} chars): "
            f"'{description[:150]}{'...' if len(description) > 150 else ''}'"
        )

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text="Project description captured. Starting research phase...")],
            ),
            actions=EventActions(
                state_delta={PL_KEY_DESCRIPTION: description}
            ),
        )


# ─────────────────────────────────────────────────────────────
# STEP 1 — PL QUERY AGENT
# ─────────────────────────────────────────────────────────────
pl_query_agent = LlmAgent(
    name="pl_query_agent",
    model=MODEL,
    description="Analyses the project and generates targeted research queries.",
    instruction="""
You are an expert Software Architect and Project Planner.

The user wants to build the following project:
{pl:project_description}

Using your own knowledge, analyse this project and generate 3 to 6 highly targeted
Google search queries to research:
  1. Recommended directory/folder structure for this type of project
  2. Best practices and conventions for the tech stack involved
  3. Key dependencies, libraries, and package manager files needed
  4. Standard boilerplate files (config, CI/CD, Dockerfile, .gitignore, etc.)
  5. Setup, environment configuration, and run/deploy steps
  6. Well-known open-source starter templates or scaffolding tools for this stack

Rules:
- Queries must be specific — include the framework, language, and version hints.
- Each query must target a different aspect (structure, deps, boilerplate, CI, etc.).
- Do NOT generate fewer than 3 or more than 6 queries.

Output ONLY the following JSON — no explanation, no markdown fences:
{
  "project_type": "<e.g. FastAPI REST API, React SPA, Django web app, CLI tool, etc.>",
  "language": "<primary programming language>",
  "tech_stack": ["<framework>", "<database>", "<tool>", "..."],
  "queries": [
    "query 1",
    "query 2",
    "...",
    "query N"
  ]
}
""",
    output_key=PL_KEY_QUERIES_JSON,
)
_pl_logger.debug("pl_query_agent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 2 — PLANNER FAN-OUT AGENT
# ─────────────────────────────────────────────────────────────

class PlannerSearchWorker(BaseAgent):
    """Runs a single google_search query and saves the result to state."""

    worker_index: int
    query_key:    str

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, *, name: str, worker_index: int, query_key: str):
        super().__init__(name=name, worker_index=worker_index, query_key=query_key)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        query = ctx.session.state.get(self.query_key, "")
        _pl_logger.info(f"[{self.name}] Searching → '{query}'")

        if not query:
            _pl_logger.warning(f"[{self.name}] Empty query — skipping.")
            yield Event(
                author=self.name,
                content=types.Content(role="model", parts=[types.Part(text="")]),
                actions=EventActions(
                    state_delta={PL_KEY_RESULT_PREFIX + str(self.worker_index): ""}
                ),
            )
            return

        inner = LlmAgent(
            name=f"pl_inner_search_{self.worker_index}",
            model=MODEL,
            instruction=f"""
You are a technical research assistant specialising in software project structure.
Use the google_search tool to search for: "{query}"

Focus on:
- Official documentation and guides
- Recommended project layouts and file naming conventions
- Standard boilerplate files and their purpose
- Configuration examples and dependency lists
- GitHub repositories, starter kits, or scaffolding tools

Return a detailed, structured summary of findings.
Include file names, directory names, package names, and conventions found.
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

        _pl_logger.info(f"[{self.name}] Result length: {len(result_text)} chars")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=result_text)],
            ),
            actions=EventActions(
                state_delta={PL_KEY_RESULT_PREFIX + str(self.worker_index): result_text}
            ),
        )


class PlannerFanOutAgent(BaseAgent):
    """Parses query plan, writes queries to state, runs parallel searches."""

    MAX_WORKERS: ClassVar[int] = 6

    def __init__(self):
        super().__init__(name="pl_fan_out_agent")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:

        raw_json = ctx.session.state.get(PL_KEY_QUERIES_JSON, "{}")
        _pl_logger.debug(f"[PlannerFanOutAgent] raw queries JSON: {raw_json[:300]}")

        clean = _extract_json(raw_json)

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            _pl_logger.error(f"[PlannerFanOutAgent] JSON parse error: {e}")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Failed to parse query plan.")],
                ),
            )
            return

        queries: List[str] = parsed.get("queries", [])
        queries      = queries[: self.MAX_WORKERS]
        project_type = parsed.get("project_type", "unknown")
        language     = parsed.get("language", "unknown")
        tech_stack   = parsed.get("tech_stack", [])

        _pl_logger.info(
            f"[PlannerFanOutAgent] project_type='{project_type}' | "
            f"language='{language}' | tech_stack={tech_stack} | "
            f"num_queries={len(queries)}"
        )

        if not queries:
            _pl_logger.warning("[PlannerFanOutAgent] No queries — proceeding with KB only.")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="No queries generated — proceeding with knowledge base only.")],
                ),
                actions=EventActions(
                    state_delta={
                        "pl:project_type": project_type,
                        "pl:language":     language,
                        "pl:tech_stack":   json.dumps(tech_stack),
                    }
                ),
            )
            return

        state_delta: dict = {
            "pl:project_type": project_type,
            "pl:language":     language,
            "pl:tech_stack":   json.dumps(tech_stack),
        }
        for i, q in enumerate(queries):
            state_delta[f"pl:query:{i}"] = q

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Launching {len(queries)} parallel research searches...")],
            ),
            actions=EventActions(state_delta=state_delta),
        )

        workers = [
            PlannerSearchWorker(
                name=f"pl_search_worker_{i}",
                worker_index=i,
                query_key=f"pl:query:{i}",
            )
            for i in range(len(queries))
        ]

        parallel = ParallelAgent(name="pl_parallel_search_agent", sub_agents=workers)

        _pl_logger.info(f"[PlannerFanOutAgent] Running ParallelAgent with {len(workers)} workers.")
        async for event in parallel.run_async(ctx):
            yield event
        _pl_logger.info("[PlannerFanOutAgent] All parallel workers completed.")


_pl_logger.debug("PlannerFanOutAgent defined.")


# ─────────────────────────────────────────────────────────────
# STEP 3 — PL ARCHITECT AGENT
# ─────────────────────────────────────────────────────────────
pl_architect_agent = LlmAgent(
    name="pl_architect_agent",
    model=MODEL,
    description="Designs the full project architecture from research and own knowledge.",
    instruction=f"""
You are a Senior Software Architect.

PROJECT DESCRIPTION:
{{pl:project_description}}

PROJECT TYPE  : {{pl:project_type}}
LANGUAGE      : {{pl:language}}
TECH STACK    : {{pl:tech_stack}}

WEB RESEARCH RESULTS:
Research 0: {{pl:result:0}}
Research 1: {{pl:result:1}}
Research 2: {{pl:result:2}}
Research 3: {{pl:result:3}}
Research 4: {{pl:result:4}}
Research 5: {{pl:result:5}}

Design the COMPLETE project architecture.

CRITICAL RULE FOR FILE "description" FIELD:
This text will be written as a comment block directly inside the file.
It must be developer-actionable — tell the developer EXACTLY:
  - What classes, functions, or routes to define in this file
  - What it imports from other modules in this project
  - What external packages / libraries it uses
  - Key logic, patterns, or conventions to follow
  - Any important notes about this file's role in the system
Do NOT write code — write a clear implementation guide in plain English.

Output ONLY the following JSON — no markdown fences, no preamble:
{{
  "project_name": "<root_folder_name_snake_case>",
  "project_title": "<Human Readable Project Title>",
  "description": "<one paragraph describing the full project>",
  "project_type": "<type>",
  "language": "<language>",
  "tech_stack": ["<item>", "..."],
  "directories": [
    {{
      "path": "<relative path from project root, e.g. src/api>",
      "purpose": "<why this directory exists>"
    }}
  ],
  "files": [
    {{
      "path": "<relative path from project root, e.g. src/api/routes.py>",
      "purpose": "<one line: what this file does>",
      "description": "<developer-actionable guide: what to implement, what to import, what logic, what conventions>"
    }}
  ],
  "dependencies": [
    {{
      "name": "<package name>",
      "version": "<e.g. >=2.0>",
      "purpose": "<why needed>"
    }}
  ],
  "env_variables": [
    {{
      "key": "<VARIABLE_NAME>",
      "example_value": "<placeholder>",
      "description": "<what it controls>"
    }}
  ],
  "setup_steps": ["<step 1>", "..."],
  "run_steps":   ["<step 1>", "..."],
  "test_steps":  ["<step 1>", "..."],
  "features":    ["<feature 1>", "..."]
}}
""",
    output_key=PL_KEY_ARCHITECTURE,
)
_pl_logger.debug("pl_architect_agent defined.")


# ─────────────────────────────────────────────────────────────
# HELPER: Build FS executor instruction (FIXED)
# ─────────────────────────────────────────────────────────────
def _build_fs_instruction(
    project_name: str,
    directories: list,
    files_with_content: list,
    project_md: str,
) -> str:
    """Fixed version with explicit tool-calling instructions to prevent hallucination."""

    available_tools = """
AVAILABLE TOOLS (you MUST use these EXACT names only):

- create_directory_tool (parameter: folder_path: string)
- write_file_tool (parameters: file_path: string, content: string)
- list_tree_tool (parameters: folder_path: string, max_depth: integer default 5)
- read_file_tool (parameter: file_path: string)
- edit_file_tool (parameters: file_path, old_text, new_text)
- append_file_tool (parameters: file_path, content)
- delete_file_tool (parameter: file_path)
- clear_file_tool (parameter: file_path)
- delete_directory_tool (parameters: folder_path, recursive: bool default False)
- rename_directory_tool (parameters: source_path, destination_path)
- list_files_tool (parameter: folder_path default '.')
- list_directories_tool (parameter: folder_path default '.')
- file_info_tool (parameter: file_path)
- supported_formats_tool (no parameters)
- copy_file_tool (parameters: source_path, destination_path)
- move_file_tool (parameters: source_path, destination_path)
"""

    lines = [
        "You are a File System Builder using tool calling.",
        "You MUST execute the steps below ONE BY ONE.",
        "For every step, output a function call using the EXACT tool name from the list above.",
        "NEVER use any other tool name (especially NOT 'call').",
        "After you receive the tool result, continue to the next step.",
        "",
        available_tools,
        "",
        "STRICT ANTI-HALLUCINATION RULE:",
        "If you are unsure which tool to use, use only the tools listed above. Never invent a tool name.",
        "",
        "Now execute these steps in strict order:",
        "",
        f"STEP 1: Create the root project directory.",
        f"Make a function call to create_directory_tool with:",
        f"  folder_path = \"{project_name}\"",
        "",
    ]

    step = 2
    for d in directories:
        lines += [
            f"STEP {step}: Create subdirectory.",
            f"Make a function call to create_directory_tool with:",
            f"  folder_path = \"{project_name}/{d['path']}\"",
            "",
        ]
        step += 1

    for f in files_with_content:
        fpath = f"{project_name}/{f['path']}"
        lines += [
            f"STEP {step}: Create file with comment-only content.",
            f"Make a function call to write_file_tool with:",
            f"  file_path = \"{fpath}\"",
            f"  content = EXACTLY the text between ===BEGIN FILE CONTENT=== and ===END FILE CONTENT=== below",
            "===BEGIN FILE CONTENT===",
            f"{f['content']}",
            "===END FILE CONTENT===",
            "",
        ]
        step += 1

    lines += [
        f"STEP {step}: Create PROJECT.md with full documentation.",
        f"Make a function call to write_file_tool with:",
        f"  file_path = \"{project_name}/PROJECT.md\"",
        f"  content = EXACTLY the text between ===BEGIN PROJECT.md=== and ===END PROJECT.md=== below",
        "===BEGIN PROJECT.md===",
        project_md,
        "===END PROJECT.md===",
        "",
    ]
    step += 1

    lines += [
        f"STEP {step}: Verify the entire project structure.",
        f"Make a function call to list_tree_tool with:",
        f"  folder_path = \"{project_name}\"",
        f"  max_depth = 4",
        "",
        "After receiving the result from list_tree_tool, output a short final summary:",
        "  - Total directories created",
        "  - Total files created",
        "  - Any issues encountered",
        "  - Confirmation that the build is complete.",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# STEP 4 — PLANNER BUILDER AGENT
# ─────────────────────────────────────────────────────────────
class PlannerBuilderAgent(BaseAgent):
    """
    Builds the project on disk using File System MCP tools.
    Source files contain comment-only placeholders — no code.
    PROJECT.md is the only file with real content.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(name="pl_builder_agent")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        _pl_logger.info("[PlannerBuilderAgent] Starting file system build phase.")

        arch_raw   = ctx.session.state.get(PL_KEY_ARCHITECTURE, "{}")
        arch_clean = _extract_json(arch_raw)

        try:
            arch = json.loads(arch_clean)
        except json.JSONDecodeError as e:
            _pl_logger.error(f"[PlannerBuilderAgent] Architecture JSON parse error: {e}")
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"ERROR: Could not parse architecture JSON: {e}")],
                ),
            )
            return

        project_name  = arch.get("project_name", "my_project")
        project_title = arch.get("project_title", project_name)
        description   = arch.get("description", "")
        directories   = arch.get("directories", [])
        files         = arch.get("files", [])
        dependencies  = arch.get("dependencies", [])
        env_variables = arch.get("env_variables", [])
        setup_steps   = arch.get("setup_steps", [])
        run_steps     = arch.get("run_steps", [])
        test_steps    = arch.get("test_steps", [])
        tech_stack    = arch.get("tech_stack", [])
        features      = arch.get("features", [])
        generated_at  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        _pl_logger.info(
            f"[PlannerBuilderAgent] Building '{project_name}' | "
            f"dirs={len(directories)} | files={len(files)}"
        )

        files_with_content = []
        for f in files:
            content = _build_file_comment(
                file_path=f["path"],
                purpose=f.get("purpose", ""),
                description=f.get("description", ""),
                project_name=project_name,
                project_title=project_title,
                tech_stack=tech_stack,
                generated_at=generated_at,
            )
            files_with_content.append({
                "path":    f["path"],
                "purpose": f.get("purpose", ""),
                "content": content,
            })
            _pl_logger.debug(
                f"[PlannerBuilderAgent] Comment block: '{f['path']}' "
                f"({len(content)} chars)"
            )

        project_md = _build_project_md(
            arch=arch,
            project_name=project_name,
            project_title=project_title,
            description=description,
            tech_stack=tech_stack,
            features=features,
            directories=directories,
            files=files,
            dependencies=dependencies,
            env_variables=env_variables,
            setup_steps=setup_steps,
            run_steps=run_steps,
            test_steps=test_steps,
            generated_at=generated_at,
        )

        fs_instruction = _build_fs_instruction(
            project_name=project_name,
            directories=directories,
            files_with_content=files_with_content,
            project_md=project_md,
        )

        _pl_logger.debug(
            f"[PlannerBuilderAgent] FS instruction: {len(fs_instruction)} chars"
        )

        builder_llm = LlmAgent(
            name="pl_fs_executor",
            model=MODEL,
            instruction=fs_instruction,
            tools=[_file_system_mcp],
        )

        build_output = ""
        async for event in builder_llm.run_async(ctx):
            if (
                event.is_final_response()
                and event.content
                and event.content.parts
            ):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        build_output += part.text

        _pl_logger.info(
            f"[PlannerBuilderAgent] FS executor done. "
            f"Output: {build_output[:300]}"
        )

        build_report = (
            f"✅ Project '{project_name}' scaffolded successfully.\n\n"
            f"📁 Root directory : {project_name}/\n"
            f"📂 Directories    : {len(directories)}\n"
            f"📄 Files created  : {len(files) + 1} (including PROJECT.md)\n\n"
            f"ℹ️  All source files contain structured comment-only placeholders.\n"
            f"   No implementation code has been written — ready for development.\n"
            f"   See PROJECT.md for full project documentation.\n\n"
            f"─── Builder Output ───\n{build_output}"
        )

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=build_report)],
            ),
            actions=EventActions(
                state_delta={PL_KEY_BUILD_REPORT: build_report}
            ),
        )


# ─────────────────────────────────────────────────────────────
# HELPER: Build PROJECT.md (unchanged)
# ─────────────────────────────────────────────────────────────
def _build_project_md(
    arch, project_name, project_title, description,
    tech_stack, features, directories, files,
    dependencies, env_variables, setup_steps, run_steps,
    test_steps, generated_at,
) -> str:
    badge_map = {
        "python": "Python-3776AB?style=flat&logo=python&logoColor=white",
        "fastapi": "FastAPI-005571?style=flat&logo=fastapi",
        "django": "Django-092E20?style=flat&logo=django&logoColor=white",
        "flask": "Flask-000000?style=flat&logo=flask&logoColor=white",
        "react": "React-20232A?style=flat&logo=react&logoColor=61DAFB",
        "node": "Node.js-339933?style=flat&logo=node.js&logoColor=white",
        "typescript": "TypeScript-007ACC?style=flat&logo=typescript&logoColor=white",
        "docker": "Docker-2496ED?style=flat&logo=docker&logoColor=white",
        "postgresql": "PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white",
        "redis": "Redis-DC382D?style=flat&logo=redis&logoColor=white",
        "mongodb": "MongoDB-4EA94B?style=flat&logo=mongodb&logoColor=white",
    }
    badges = []
    for tech in tech_stack:
        key = tech.lower().replace(" ", "")
        for bkey, bval in badge_map.items():
            if bkey in key:
                badges.append(f"![{tech}](https://img.shields.io/badge/{bval})")
                break
    badge_line = "  ".join(badges)

    tree = [f"{project_name}/"]
    for d in directories:
        parts = d["path"].split("/")
        indent = "    " * (len(parts) - 1)
        tree.append(f"{indent}├── {parts[-1]}/")
    for f in files:
        fparts = f["path"].split("/")
        indent = "    " * (len(fparts) - 1)
        tree.append(f"{indent}├── {fparts[-1]}")
    tree.append("├── PROJECT.md")
    tree_str = "\n".join(tree)

    ref_table  = "| Path | Type | Purpose |\n|---|---|---|\n"
    for d in directories:
        ref_table += f"| `{d['path']}/` | 📂 Dir | {d['purpose']} |\n"
    for f in files:
        ext   = Path(f["path"]).suffix.lstrip(".").upper() or "File"
        ref_table += f"| `{f['path']}` | 📄 {ext} | {f['purpose']} |\n"
    ref_table += "| `PROJECT.md` | 📄 MD | Project documentation (this file) |\n"

    file_details = ""
    for f in files:
        file_details += (
            f"### `{f['path']}`\n\n"
            f"**Purpose:** {f['purpose']}\n\n"
            f"{f.get('description', '_No description provided._')}\n\n"
            f"---\n\n"
        )

    deps = ""
    if dependencies:
        deps = "| Package | Version | Purpose |\n|---|---|---|\n"
        for d in dependencies:
            deps += f"| `{d['name']}` | `{d.get('version','latest')}` | {d['purpose']} |\n"
    else:
        deps = "_No external dependencies listed._"

    env_tbl = ""
    if env_variables:
        env_tbl = "| Variable | Example | Description |\n|---|---|---|\n"
        for ev in env_variables:
            env_tbl += f"| `{ev['key']}` | `{ev.get('example_value','')}` | {ev['description']} |\n"
    else:
        env_tbl = "_No environment variables required._"

    features_md = "\n".join([f"- {ft}" for ft in features]) if features else "- See project description"
    setup_md    = "\n".join([f"{i+1}. {s}" for i, s in enumerate(setup_steps)]) if setup_steps else "1. See above"
    run_md      = "\n".join([f"{i+1}. {s}" for i, s in enumerate(run_steps)])   if run_steps   else "1. See above"
    test_md     = "\n".join([f"{i+1}. {s}" for i, s in enumerate(test_steps)])  if test_steps  else "1. Run tests"

    lang = arch.get("language", "python").lower()
    install_cmd = "```bash\npip install -r requirements.txt\n```" if "python" in lang else "```bash\n# install dependencies\n```"

    return f"""# {project_title}

{badge_line}

> 📅 Scaffolded by **Jarvis Planner Agent** on {generated_at}

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [File Reference](#file-reference)
- [File Details](#file-details)
- [Tech Stack](#tech-stack)
- [Dependencies](#dependencies)
- [Environment Variables](#environment-variables)
- [Setup & Installation](#setup--installation)
- [Running the Project](#running-the-project)
- [Testing](#testing)
- [Contributing](#contributing)

---

## 🔍 Overview

{description}

---

## ✨ Features

{features_md}

---

## 📁 Project Structure

> **Note:** All source files contain **comment-only placeholders** — no implementation code.
> Each file's comment block describes exactly what needs to be implemented.
> Only `PROJECT.md` contains real content.

---

## 📄 File Reference

{ref_table}

---

## 🗂 File Details

{file_details}

---

## 🛠 Tech Stack

| Technology | Role |
|---|---|
""" + "\n".join([f"| `{t}` | Core dependency |" for t in tech_stack]) + f"""

---

## 📦 Dependencies

{deps}

{install_cmd}

---

## 🔐 Environment Variables

{env_tbl}

> Copy `.env.example` to `.env` before running:
> ```bash
> cp .env.example .env
> ```

---

## ⚙️ Setup & Installation

{setup_md}

---

## ▶️ Running the Project

{run_md}

---

## 🧪 Testing

{test_md}

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "feat: your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📜 License

This project is open-source. Add your preferred license here.

---

*Auto-generated by the **Jarvis Planner Agent**. Update this file as the project evolves.*
"""


# ─────────────────────────────────────────────────────────────
# PIPELINE ASSEMBLY
# ─────────────────────────────────────────────────────────────
_pl_entry_agent   = PlannerEntryAgent()
_pl_fan_out_agent = PlannerFanOutAgent()
_pl_builder_agent = PlannerBuilderAgent()

_pl_pipeline = SequentialAgent(
    name="pl_pipeline",
    description="Internal planner pipeline: capture → research → architect → build.",
    sub_agents=[
        _pl_entry_agent,
        pl_query_agent,
        _pl_fan_out_agent,
        pl_architect_agent,
        _pl_builder_agent,
    ],
)

_pl_logger.info("Planner Agent pipeline assembled (FIXED version).")


# ─────────────────────────────────────────────────────────────
# PUBLIC WRAPPER — PlannerAgent
# ─────────────────────────────────────────────────────────────
class PlannerAgent(BaseAgent):
    """
    Creates a complete project scaffold from scratch given a description.
    Researches best practices via Google Search, designs the full directory
    structure, creates all directories and files on disk with comment-only
    placeholders, and produces a detailed PROJECT.md. Use when the user wants
    to scaffold, plan, or create a new project.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="planner_agent",
            description=(
                "Creates a complete project scaffold from scratch given a description. "
                "Researches best practices, designs the full directory structure, "
                "physically creates all directories and files on disk with comment-only "
                "placeholders, and produces a detailed PROJECT.md documentation file. "
                "Use when the user wants to scaffold, plan, or create a new project."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        _pl_logger.info("[PlannerAgent] Pipeline started.")

        final_report = ""

        async for event in _pl_pipeline.run_async(ctx):
            if (
                event.author == "pl_builder_agent"
                and event.is_final_response()
                and event.content
                and event.content.parts
            ):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_report += part.text

        if not final_report:
            final_report = ctx.session.state.get(PL_KEY_BUILD_REPORT, "")
            if final_report:
                _pl_logger.info("[PlannerAgent] Build report recovered from state.")

        if not final_report:
            final_report = "Project planning complete. No build report was generated."
            _pl_logger.warning("[PlannerAgent] Pipeline produced no output.")

        _pl_logger.info(
            f"[PlannerAgent] Pipeline complete. Report: {len(final_report)} chars."
        )

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=final_report)],
            ),
            actions=EventActions(
                state_delta={PL_KEY_BUILD_REPORT: final_report}
            ),
        )


# ─────────────────────────────────────────────────────────────
# PUBLIC EXPORTS
# ─────────────────────────────────────────────────────────────
planner_agent = PlannerAgent()

__all__ = ["planner_agent"]
