# blog_gen_a2a/blog_generation/agent.py
#
# Exposes BlogWriting LangGraph agent as an A2A-compliant HTTP server.
#
# Usage:
#   uvicorn blog_gen_a2a.blog_generation.agent:a2a_app --host localhost --port 8002
# ─────────────────────────────────────────────────────────────────────────────

import re
import asyncio
import logging
import uvicorn

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    TaskState,
)
from a2a.utils import new_task

# ── Import your compiled LangGraph app ────────────────────────────────────────
from .BlogWriting import app as langgraph_app

logger = logging.getLogger("BlogAgentServer")


# ─────────────────────────────────────────────────────────────────────────────
# Helper — strip ADK context metadata injected by RemoteA2aAgent
# ─────────────────────────────────────────────────────────────────────────────

def _extract_clean_topic(raw: str) -> str:
    """
    ADK's RemoteA2aAgent prepends conversation history as 'For context: ...'
    lines before the actual user message.  Strip all of those lines and return
    only the clean user-written topic.

    Example raw input:
        Hey
        For context:
        [root_agent] said: Hello! How can I help you today?

        Today is 11th March 2026. Write a blog on Agentic AI
        For context:
        [root_agent] called tool `transfer_to_agent` ...

    Returns:
        "Today is 11th March 2026. Write a blog on Agentic AI"
    """
    lines = raw.splitlines()
    clean_lines = []
    skip_next_blank = False

    for line in lines:
        stripped = line.strip()

        # Skip "For context:" marker lines and the indented lines that follow
        if stripped == "For context:":
            skip_next_blank = True
            # Also remove the last accumulated line if it was a stray "Hey" / greeting
            if clean_lines and len(clean_lines[-1].strip()) <= 10:
                clean_lines.pop()
            continue

        if skip_next_blank:
            # Skip the bracketed context block (non-empty lines after "For context:")
            if stripped:
                continue
            else:
                skip_next_blank = False
                continue

        clean_lines.append(line)

    topic = "\n".join(clean_lines).strip()

    # Final fallback: if nothing survived, return the raw string as-is
    return topic if topic else raw.strip()


# ─────────────────────────────────────────────────────────────────────────────
# AgentExecutor  ── bridge between A2A and your LangGraph pipeline
# ─────────────────────────────────────────────────────────────────────────────

class BlogWritingAgentExecutor(AgentExecutor):
    """
    Receives a plain-text topic from the A2A caller,
    runs it through the BlogWriting LangGraph pipeline,
    and streams keep-alive status pings every 30 s so the root ADK agent
    never times out — even for long research + writing jobs.
    """

    def __init__(self):
        self.agent = langgraph_app

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        # 1. Extract and clean the user's text prompt
        raw_input: str = context.get_user_input()
        topic: str = _extract_clean_topic(raw_input)
        logger.info(f"[EXECUTOR] Raw input  : {repr(raw_input[:120])}")
        logger.info(f"[EXECUTOR] Clean topic: {repr(topic)}")

        # 2. Create / register the task so the client can track it
        task = context.current_task
        if task is None:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # 3. Signal "working"
        await updater.update_status(
            TaskState.working,
            message=updater.new_agent_message(
                parts=[{"kind": "text", "text": f"Starting blog pipeline for: '{topic}'"}]
            ),
        )

        # Progress messages sent as keep-alive pings every 30 s.
        progress_messages = [
            "Step 1/5 — Routing: deciding whether web research is needed...",
            "Step 2/5 — Research: searching the web for relevant sources...",
            "Step 3/5 — Orchestrating: generating the blog outline and section plan...",
            "Step 4/5 — Writing: all blog sections are being written in parallel...",
            "Step 5/5 — Reducing: assembling and saving the final blog post...",
        ]

        try:
            # 4. Launch the LangGraph pipeline in a background thread so the
            #    async event loop stays free to send keep-alive pings.
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None,
                lambda: self.agent.invoke(
                    {
                        "topic": topic,
                        "mode": "",
                        "needs_research": False,
                        "queries": [],
                        "evidence": [],
                        "plan": None,
                        "sections": [],
                        "final": "",
                    }
                ),
            )

            # 5. Send a progress ping every 30 s while the pipeline is running.
            #    This keeps the HTTP connection alive for arbitrarily long jobs.
            ping_index = 0
            while not future.done():
                await asyncio.sleep(30)
                if not future.done():
                    msg = progress_messages[min(ping_index, len(progress_messages) - 1)]
                    logger.info(f"[EXECUTOR] Keep-alive ping {ping_index + 1}: {msg}")
                    await updater.update_status(
                        TaskState.working,
                        message=updater.new_agent_message(
                            parts=[{"kind": "text", "text": msg}]
                        ),
                    )
                    ping_index += 1

            # 6. Retrieve the result (re-raises any exception thrown in the thread)
            result = await future
            final_md: str = result.get("final", "").strip()

            if not final_md:
                raise ValueError("LangGraph pipeline returned an empty blog post.")

            logger.info(f"[EXECUTOR] Blog generated — ~{len(final_md.split())} words")

            # 7. Return the finished blog as a text artifact
            await updater.add_artifact(
                parts=[{"kind": "text", "text": final_md}],
                artifact_id="blog-output",
                name="Blog Post (Markdown)",
            )
            await updater.complete()

        except Exception as exc:
            logger.error(f"[EXECUTOR] Pipeline failed: {exc}", exc_info=True)
            await updater.update_status(
                TaskState.failed,
                message=updater.new_agent_message(
                    parts=[{"kind": "text", "text": f"Blog generation failed: {exc}"}]
                ),
            )
            raise

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Called when the A2A client requests task cancellation.
        The LangGraph pipeline runs synchronously in a thread and cannot be
        interrupted mid-flight, so we simply mark the task as cancelled.
        """
        task = context.current_task
        if task is None:
            return

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.update_status(
            TaskState.canceled,
            message=updater.new_agent_message(
                parts=[{"kind": "text", "text": "Task was cancelled by the client."}]
            ),
        )
        logger.info(f"[EXECUTOR] Task {task.id} cancelled.")


# ─────────────────────────────────────────────────────────────────────────────
# Agent Card  ── metadata served at /.well-known/agent.json
# streaming=True keeps the response stream open for keep-alive pings.
# ─────────────────────────────────────────────────────────────────────────────

def get_agent_card(host: str = "localhost", port: int = 8002) -> AgentCard:
    return AgentCard(
        name="blog_writing_agent",
        description=(
            "LangGraph-powered technical blog writer. "
            "Given a topic, it plans, optionally researches, "
            "and writes a complete Markdown blog post."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="write_blog_post",
                name="write_blog_post",
                description=(
                    "Write a structured technical blog post on any topic. "
                    "Supports evergreen explainers, tutorials, news roundups, "
                    "comparisons, and system-design write-ups."
                ),
                tags=["blog", "writing", "research", "markdown", "technical"],
                examples=[
                    "Write a blog on Self Attention",
                    "Write a blog on the Future of Quantum AI",
                    "Write a tutorial on LangGraph for beginners",
                    "Write a news roundup on the latest LLM releases this week",
                ],
            )
        ],
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Build the Starlette A2A app
# ─────────────────────────────────────────────────────────────────────────────

def build_a2a_app(host: str = "localhost", port: int = 8002):
    agent_card = get_agent_card(host, port)

    request_handler = DefaultRequestHandler(
        agent_executor=BlogWritingAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    return server.build()


# Module-level app — used when running via uvicorn
a2a_app = build_a2a_app()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "blog_gen_a2a.blog_generation.agent:a2a_app",
        host="localhost",
        port=8002,
        reload=False,
        log_level="info",
    )

# uvicorn blog_gen_a2a.blog_generation.agent:a2a_app --host localhost --port 8002
