from __future__ import annotations

import re
import logging
import operator
from datetime import datetime
from typing import TypedDict, List, Annotated, Literal, Optional
from pydantic import BaseModel, Field
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_tavily import TavilySearch
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

#------------------------------
# Logger Setup
#------------------------------

def setup_logger() -> logging.Logger:
    """Create a logger that writes to both console and a timestamped log file.

    Log files are saved under the 'logs/' directory with the naming format:
        log_{YYYYMMDD}_{HHMMSS}.log
    The directory is created automatically if it does not exist.
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = logs_dir / f"log_{timestamp}.log"

    logger = logging.getLogger("BlogWriter")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logger is called more than once
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — DEBUG and above saved to log file
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler — INFO and above printed to stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logger initialised. Log file: {log_filename}")
    return logger

logger = setup_logger()


#------------------------------
# Schemas
#------------------------------

class Task(BaseModel):
    id: int
    title: str
    goal: str = Field(
        ...,
        description="One sentence describing what the reader should be able to do/understand after this section."
    )
    bullets: List[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3-6 concrete, non-overlapping subpoints to cover in this section."
    )
    target_words: int = Field(
        ...,
        description="Target word count for this section (120-450)."
    )
    tags: List[str] = Field(default_factory=list)
    requires_research: bool = False
    requires_citations: bool = False
    requires_code: bool = False


class Plan(BaseModel):
    blog_title: str
    audience: str
    tone: str
    blog_kind: Literal["explainer", "tutorial", "news_roundup", "comparison", "system_design"] = "explainer"
    constraints: List[str] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    title: str
    url: str
    published_at: Optional[str] = None
    snippet: Optional[str] = None
    source: Optional[str] = None


class RouterDecision(BaseModel):
    needs_research: bool = False
    # Added default "closed_book" so if the LLM fails to emit a valid
    # mode value, we don't get a ValidationError that crashes the router.
    mode: Literal["closed_book", "hybrid", "open_book"] = "closed_book"
    queries: List[str] = Field(default_factory=list)


class EvidencePack(BaseModel):
    evidence: List[EvidenceItem] = Field(default_factory=list)


#------------------------------
# State
#------------------------------

class State(TypedDict):
    topic: str

    # routing / research
    mode: str
    needs_research: bool
    queries: List[str]
    evidence: List[EvidenceItem]
    plan: Optional[Plan]

    # workers
    sections: Annotated[List[tuple[int, str]], operator.add]
    final: str


#------------------------------
# LLM
#------------------------------

logger.debug("[SETUP] Initialising LLMs...")
blog_llm = ChatOllama(model="llama3.2:3b", temperature=0.5)
# qwen3:0.6b emits <think> tokens which break structured output — use llama3.2:3b here too
decision_llm = ChatOllama(model="llama3.2:3b", temperature=0.7)
logger.debug("[SETUP] LLMs ready. blog_llm=llama3.2:3b | decision_llm=llama3.2:3b")


#------------------------------
# Router
#------------------------------

ROUTER_SYSTEM = """You are a routing module for a technical blog planner.

Decide whether web research is needed BEFORE planning.

Modes:
- closed_book (needs_research=false):
  Evergreen topic where correctness does not depend on recent facts (concepts, fundamentals).
- hybrid (needs_research=true):
  Mostly evergreen but needs up-to-date examples/tools/models to be useful.
- open_book (needs_research=true):
  Mostly volatile: weekly roundups, "this week", "latest", ranking, pricing, policy/regulation.

If needs_research=true:
- Output 3-10 high-signal queries.
- Queries should be scoped and specific (avoid generic queries like just "AI" or "LLM").
- If user asked for "last week/this week/latest", reflect that constraint IN THE QUERIES.
"""

def router_node(state: State) -> dict:
    topic = state["topic"]
    logger.info("[ROUTER] ── START ──────────────────────────────────────")
    logger.info(f"[ROUTER] Topic received: '{topic}'")
    logger.debug("[ROUTER] Invoking decision LLM with structured output (RouterDecision)...")

    decider = decision_llm.with_structured_output(RouterDecision)
    decision = decider.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=f"Topic: {topic}"),
        ]
    )

    # If the LLM emits queries but sets needs_research=False, force research to run.
    needs_research = decision.needs_research or bool(decision.queries)

    logger.info(f"[ROUTER] Decision => mode='{decision.mode}' | needs_research={needs_research} | num_queries={len(decision.queries)}")
    for i, q in enumerate(decision.queries, 1):
        logger.debug(f"[ROUTER]   Query {i}: {q}")
    logger.info("[ROUTER] ── END ────────────────────────────────────────")

    return {
        "needs_research": needs_research,
        "mode": decision.mode,
        "queries": decision.queries,
    }


def route_next(state: State) -> str:
    next_node = "research" if state["needs_research"] else "orchestrator"
    logger.info(f"[ROUTER] Routing graph → '{next_node}'")
    return next_node


#------------------------------
# Research
#------------------------------

def _tavily_search(query: str, max_results: int = 5) -> List[dict]:
    logger.debug(f"[TAVILY] Searching: '{query}' (max_results={max_results})")
    # tool = TavilySearchResults(max_results=max_results)
    tool = TavilySearch(max_results=max_results)
    response = tool.invoke({"query": query})

    # langchain_tavily.TavilySearch returns a dict: {"query": ..., "results": [...]}
    # whereas the old TavilySearchResults returned a plain list.
    # Extract the "results" list; fall back gracefully if the shape is unexpected.
    if isinstance(response, dict):
        results = response.get("results") or []
    elif isinstance(response, list):
        results = response  # legacy / alternative wrapper — keep working
    else:
        results = []

    logger.debug(f"[TAVILY] Raw hits received: {len(results)} for query '{query}'")

    normalized: List[dict] = []
    for r in results or []:
        normalized.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": r.get("content") or r.get("snippet") or "",
                "published_at": r.get("published_date") or r.get("published_at"),
                "source": r.get("source"),
            }
        )
    logger.debug(f"[TAVILY] Normalised {len(normalized)} results for query '{query}'")
    return normalized


RESEARCH_SYSTEM = """You are a research synthesizer for technical writing.

Given raw web search results, produce a deduplicated list of EvidenceItem objects.

Rules:
- Only include items with a non-empty url.
- Prefer relevant + authoritative sources (company blogs, docs, reputable outlets).
- If a published date is explicitly present in the result payload, keep it as YYYY-MM-DD.
  If missing or unclear, set published_at=null. Do NOT guess.
- Keep snippets short.
- Deduplicate by URL.
"""

def research_node(state: State) -> dict:
    queries = (state.get("queries", []) or [])
    max_results = 6

    logger.info("[RESEARCH] ── START ─────────────────────────────────────")
    logger.info(f"[RESEARCH] {len(queries)} search queries to run (max_results={max_results} each)")

    raw_results: List[dict] = []
    for i, q in enumerate(queries, 1):
        logger.info(f"[RESEARCH] Query {i}/{len(queries)}: '{q}'")
        results = _tavily_search(q, max_results=max_results)
        raw_results.extend(results)
        logger.debug(f"[RESEARCH] Cumulative raw results so far: {len(raw_results)}")

    logger.info(f"[RESEARCH] Total raw results collected: {len(raw_results)}")

    if not raw_results:
        logger.warning("[RESEARCH] No raw results found — returning empty evidence.")
        logger.info("[RESEARCH] ── END ──────────────────────────────────────")
        return {"evidence": []}

    logger.debug("[RESEARCH] Invoking blog LLM to extract and deduplicate EvidenceItems...")
    extractor = blog_llm.with_structured_output(EvidencePack)
    pack = extractor.invoke(
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=f"Raw results:\n{raw_results}"),
        ]
    )

    dedup = {}
    for e in pack.evidence:
        if e.url:
            dedup[e.url] = e

    logger.info(f"[RESEARCH] Evidence items after deduplication: {len(dedup)}")
    for idx, url in enumerate(dedup.keys(), 1):
        logger.debug(f"[RESEARCH]   Evidence {idx}: {url}")
    logger.info("[RESEARCH] ── END ──────────────────────────────────────")

    return {"evidence": list(dedup.values())}


#------------------------------
# Orchestrator
#------------------------------

ORCH_SYSTEM = """You are a senior technical writer and developer advocate.
Your job is to produce a highly actionable outline for a technical blog post.

Hard requirements:
- Create 5-9 sections (tasks) suitable for the topic and audience.
- Each task must include:
  1) goal (1 sentence)
  2) 3-6 bullets that are concrete, specific, and non-overlapping
  3) target word count (120-550)
- You MUST populate the tasks array. An empty tasks list is invalid.

Quality bar:
- Assume the reader is a developer; use correct terminology.
- Bullets must be actionable: build/compare/measure/verify/debug.
- Ensure the overall plan includes at least 2 of these somewhere:
  * minimal code sketch / MWE (set requires_code=True for that section)
  * edge cases / failure modes
  * performance / cost considerations
  * security / privacy considerations (if relevant)
  * debugging / observability tips

Grounding rules:
- Mode closed_book: keep it evergreen; do not depend on evidence.
- Mode hybrid:
  - Use evidence for up-to-date examples (models/tools/releases) in bullets.
  - Mark sections using fresh info as requires_research=True and requires_citations=True.
- Mode open_book:
  - Set blog_kind = "news_roundup".
  - Every section is about summarizing events + implications.
  - DO NOT include tutorial/how-to sections unless user explicitly asked for that.
  - If evidence is empty or insufficient, create a plan that transparently says "insufficient sources".

Example of a valid filled output (use this structure, NOT these exact values):
{
  "blog_title": "Understanding Gradient Descent",
  "audience": "developers",
  "tone": "informative",
  "blog_kind": "explainer",
  "constraints": [],
  "tasks": [
    {
      "id": 1,
      "title": "What is Gradient Descent",
      "goal": "Explain what gradient descent is and why it matters for training ML models.",
      "bullets": [
        "Define the loss surface and what it means to minimize it",
        "Explain the role of the gradient as a direction of steepest ascent",
        "Describe the update rule: theta = theta - lr * grad"
      ],
      "target_words": 200,
      "tags": ["fundamentals"],
      "requires_research": false,
      "requires_citations": false,
      "requires_code": false
    },
    {
      "id": 2,
      "title": "Implementing Gradient Descent in Python",
      "goal": "Show a minimal working implementation of gradient descent from scratch.",
      "bullets": [
        "Define a simple quadratic loss function",
        "Implement the gradient update loop",
        "Plot the loss curve to verify convergence"
      ],
      "target_words": 300,
      "tags": ["code"],
      "requires_research": false,
      "requires_citations": false,
      "requires_code": true
    }
  ]
}

Output must strictly match the Plan schema.
"""

def orchestrator_node(state: State) -> dict:
    """Planner — generates a structured blog outline."""
    logger.info("[ORCHESTRATOR] ── START ──────────────────────────────────")
    logger.info(f"[ORCHESTRATOR] Topic: '{state['topic']}' | Mode: '{state.get('mode', 'closed_book')}'")

    planner = blog_llm.with_structured_output(Plan)
    evidence = state.get("evidence", [])
    mode = state.get("mode", "closed_book")

    logger.debug(f"[ORCHESTRATOR] Evidence items available for context: {len(evidence)}")

    messages = [
        SystemMessage(content=ORCH_SYSTEM),
        HumanMessage(
            content=(
                f"Topic: {state['topic']}\n"
                f"Mode: {mode}\n\n"
                f"Evidence (ONLY use for fresh claims; may be empty):\n"
                f"{[e.model_dump() for e in evidence][:16]}"
            )
        ),
    ]

    plan = None
    for attempt in range(3):
        logger.info(f"[ORCHESTRATOR] Planning attempt {attempt + 1}/3...")
        plan = planner.invoke(messages)

        if plan.tasks:
            logger.info(f"[ORCHESTRATOR] Plan accepted: {len(plan.tasks)} tasks generated.")
            logger.debug(f"[ORCHESTRATOR] Blog title : '{plan.blog_title}'")
            logger.debug(f"[ORCHESTRATOR] Audience   : '{plan.audience}'")
            logger.debug(f"[ORCHESTRATOR] Tone       : '{plan.tone}'")
            logger.debug(f"[ORCHESTRATOR] Blog kind  : '{plan.blog_kind}'")
            for t in plan.tasks:
                logger.debug(
                    f"[ORCHESTRATOR]   Task {t.id:02d}: '{t.title}' "
                    f"| ~{t.target_words}w | code={t.requires_code} | citations={t.requires_citations}"
                )
            break

        logger.warning(f"[ORCHESTRATOR] Attempt {attempt + 1} returned empty tasks — escalating prompt...")
        messages = [
            SystemMessage(content=ORCH_SYSTEM),
            HumanMessage(
                content=(
                    f"Topic: {state['topic']}\n"
                    f"Mode: {mode}\n\n"
                    f"IMPORTANT: You returned an empty tasks list. This is invalid.\n"
                    f"You MUST include at least 5 task objects in the tasks array.\n"
                    f"Follow the example in the system prompt exactly.\n\n"
                    f"Evidence (ONLY use for fresh claims; may be empty):\n"
                    f"{[e.model_dump() for e in evidence][:16]}"
                )
            ),
        ]

    if not plan or not plan.tasks:
        logger.error("[ORCHESTRATOR] All 3 attempts produced empty tasks. Pipeline will fail.")

    logger.info("[ORCHESTRATOR] ── END ────────────────────────────────────")
    return {"plan": plan}


#------------------------------
# Sub-worker dispatcher
#------------------------------

def sub_worker(state: State):
    logger.info("[DISPATCHER] ── START ────────────────────────────────────")

    if not state.get("plan") or not state["plan"].tasks:
        logger.error("[DISPATCHER] No tasks in plan — aborting pipeline.")
        raise ValueError(
            "Orchestrator produced no tasks after all retries. "
            "Cannot generate blog sections. Try a more capable model."
        )

    tasks = state["plan"].tasks
    logger.info(f"[DISPATCHER] Dispatching {len(tasks)} parallel worker(s)...")
    for t in tasks:
        logger.debug(f"[DISPATCHER]   → Worker for Task {t.id}: '{t.title}'")
    logger.info("[DISPATCHER] ── END ──────────────────────────────────────")

    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])]
            },
        )
        for task in tasks
    ]


#------------------------------
# Worker
#------------------------------

WORKER_SYSTEM = """You are a senior technical writer and developer advocate.
Write ONE section of a technical blog post in Markdown.

Hard constraints:
- Follow the provided Goal and cover ALL Bullets in order (do not skip or merge bullets).
- Stay close to Target words (±15%).
- Output ONLY the section content in Markdown (no blog title H1, no extra commentary).
- Start with a '## <Section Title>' heading.

Scope guard:
- If blog_kind == "news_roundup": do NOT turn this into a tutorial/how-to guide.
  Focus on summarizing events and implications.

Grounding policy:
- If mode == open_book:
  - Do NOT introduce any specific event/company/model/funding/policy claim unless it is
    supported by a provided Evidence URL.
  - For each event claim, attach a source as a Markdown link: ([Source](URL)).
  - Only use URLs provided in Evidence. If not supported, write: "Not found in provided sources."
- If requires_citations == true:
  - For outside-world claims, cite Evidence URLs the same way.
- Evergreen reasoning is OK without citations unless requires_citations is true.

Code:
- If requires_code == true, include at least one minimal, correct code snippet.

Style:
- Short paragraphs, bullets where helpful, code fences for code.
- Avoid fluff/marketing. Be precise and implementation-oriented.
"""


def worker_node(payload: dict) -> dict:
    """Writes one blog section in parallel with other workers."""
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]
    topic = payload["topic"]
    mode = payload.get("mode", "closed_book")

    logger.info(f"[WORKER] ── Task {task.id}: '{task.title}' ─────────────────")
    logger.debug(f"[WORKER]   Goal           : {task.goal}")
    logger.debug(f"[WORKER]   Target words   : {task.target_words}")
    logger.debug(f"[WORKER]   requires_code  : {task.requires_code}")
    logger.debug(f"[WORKER]   requires_cit.  : {task.requires_citations}")
    logger.debug(f"[WORKER]   Bullets ({len(task.bullets)})   : {task.bullets}")
    logger.debug(f"[WORKER]   Evidence items : {len(evidence)}")

    bullets_text = "\n- " + "\n- ".join(task.bullets)

    evidence_text = ""
    if evidence:
        evidence_text = "\n".join(
            f"- {e.title} | {e.url} | {e.published_at or 'date:unknown'}".strip()
            for e in evidence[:20]
        )

    logger.debug(f"[WORKER]   Invoking blog LLM to write section...")
    section_md = blog_llm.invoke(
        [
            SystemMessage(content=WORKER_SYSTEM),
            HumanMessage(
                content=(
                    f"Blog title: {plan.blog_title}\n"
                    f"Audience: {plan.audience}\n"
                    f"Tone: {plan.tone}\n"
                    f"Blog kind: {plan.blog_kind}\n"
                    f"Constraints: {plan.constraints}\n"
                    f"Topic: {topic}\n"
                    f"Mode: {mode}\n\n"
                    f"Section title: {task.title}\n"
                    f"Goal: {task.goal}\n"
                    f"Target words: {task.target_words}\n"
                    f"Tags: {task.tags}\n"
                    f"requires_research: {task.requires_research}\n"
                    f"requires_citations: {task.requires_citations}\n"
                    f"requires_code: {task.requires_code}\n"
                    f"Bullets:{bullets_text}\n\n"
                    f"Evidence (ONLY use these URLs when citing):\n{evidence_text}\n"
                )
            )
        ],
    ).content.strip()

    word_count = len(section_md.split())
    logger.info(f"[WORKER] Task {task.id} done — '{task.title}' | ~{word_count} words written")

    return {"sections": [(task.id, section_md)]}


#------------------------------
# Reducer
#------------------------------

def reducer_node(state: State) -> dict:
    """Stitches all worker sections into the final markdown blog post."""
    plan = state["plan"]
    sections = state["sections"]

    logger.info("[REDUCER] ── START ───────────────────────────────────────")
    logger.info(f"[REDUCER] Assembling {len(sections)} section(s) for blog: '{plan.blog_title}'")

    ordered_sections = [md for _, md in sorted(sections, key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    final_md = f"# {plan.blog_title}\n\n{body}\n"

    total_words = len(final_md.split())
    logger.info(f"[REDUCER] Total blog word count: ~{total_words}")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize blog title for use as a filename
    safe_title = re.sub(r"[^\w\s-]", "_", plan.blog_title).strip()
    filename = output_dir / f"{safe_title}.md"
    filename.write_text(final_md, encoding="utf-8")

    logger.info(f"[REDUCER] Blog saved → {filename}")
    logger.info("[REDUCER] ── END ─────────────────────────────────────────")

    return {"final": final_md}


#------------------------------
# Graph
#------------------------------

logger.debug("[SETUP] Building LangGraph state graph...")
g = StateGraph(State)

g.add_node("router", router_node)
g.add_node("research", research_node)
g.add_node("orchestrator", orchestrator_node)
g.add_node("worker", worker_node)
g.add_node("reducer", reducer_node)

g.add_edge(START, "router")
g.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
g.add_edge("research", "orchestrator")
g.add_conditional_edges("orchestrator", sub_worker, ["worker"])
g.add_edge("worker", "reducer")
g.add_edge("reducer", END)

app = g.compile()
logger.debug("[SETUP] LangGraph compiled successfully.")


# #------------------------------
# # Runner
# #------------------------------

# def run(topic: str):
#     logger.info("=" * 65)
#     logger.info("[RUN] Blog generation pipeline STARTING")
#     logger.info(f"[RUN] Topic : '{topic}'")
#     logger.info("=" * 65)

#     out = app.invoke(
#         {
#             "topic": topic,
#             "mode": "",
#             "needs_research": False,
#             "queries": [],
#             "evidence": [],
#             "plan": None,
#             "sections": [],
#             "final": "",
#         }
#     )

#     logger.info("=" * 65)
#     logger.info("[RUN] Pipeline COMPLETE")
#     logger.info("=" * 65)
#     return out


# query = "Write a blog on the Future of Quantum AI. The capability of Artificial Intellegence using the power of Quantum Computing."
# response = run(query)
# logger.info("[RESPONSE] Blog Generation Complete.")

# print("\n"*2)
# print(response)
# print("\n"*2)
