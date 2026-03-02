# app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from chatbot import chat_stream, session_service, APP_NAME, USER_ID
import uuid
import json
from datetime import datetime, timezone

app = FastAPI(title="Jarvis Chatbot")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory session metadata store: { session_id: { name, created_at } }
# For production, persist this in your database.
session_meta: dict = {}

# ─────────────────────────────────────────
# Helper: extract a UTC ISO timestamp from an ADK session object
# (handles both datetime objects and numeric epoch timestamps)
# ─────────────────────────────────────────
def _session_timestamp(s) -> str:
    """
    Try to get a meaningful creation timestamp from an ADK Session object.
    Falls back to the current UTC time so that unknown sessions always
    appear under 'Today' rather than 'Older'.
    """
    for attr in ("create_time", "last_update_time"):
        val = getattr(s, attr, None)
        if val is None:
            continue
        # datetime-like objects
        if hasattr(val, "isoformat"):
            return val.isoformat()
        # Numeric epoch (seconds or milliseconds)
        try:
            num = float(val)
            if num > 1e10:          # milliseconds → seconds
                num /= 1000
            return datetime.fromtimestamp(num, tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
        # String fallback
        if isinstance(val, str) and val:
            return val
    # Nothing found — use now so the session lands in "Today"
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────
# Home page
# ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    sessions_response = await session_service.list_sessions(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    sessions = []
    if sessions_response and sessions_response.sessions:
        for s in sessions_response.sessions:
            sid = s.id
            meta = session_meta.get(sid, {})

            # ── Fix: recover created_at from the ADK session when session_meta
            #         was cleared (e.g. after an app restart).
            created_at = meta.get("created_at", "")
            if not created_at:
                created_at = _session_timestamp(s)
                # Cache it so subsequent requests are fast
                session_meta.setdefault(sid, {})["created_at"] = created_at

            sessions.append({
                "id":         sid,
                "name":       meta.get("name", sid[:8] + "…"),
                "created_at": created_at,
            })
        # Sort newest first
        sessions.sort(key=lambda x: x["created_at"], reverse=True)

    return templates.TemplateResponse("index.html", {
        "request":  request,
        "sessions": sessions,
    })


# ─────────────────────────────────────────
# New chat
# ─────────────────────────────────────────
@app.post("/new_chat")
async def new_chat():
    new_session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=new_session_id,
    )
    session_meta[new_session_id] = {
        "name":       "New Chat",
        "created_at": now,
    }
    return JSONResponse({
        "session_id": new_session_id,
        "name":       "New Chat",
        "created_at": now,
    })


# ─────────────────────────────────────────
# Rename session
# ─────────────────────────────────────────
@app.patch("/session/{session_id}/rename")
async def rename_session(session_id: str, request: Request):
    body = await request.json()
    new_name = body.get("name", "").strip()
    if not new_name:
        return JSONResponse({"error": "Name cannot be empty"}, status_code=400)
    if session_id not in session_meta:
        session_meta[session_id] = {"created_at": datetime.now(timezone.utc).isoformat()}
    session_meta[session_id]["name"] = new_name
    return JSONResponse({"session_id": session_id, "name": new_name})


# ─────────────────────────────────────────
# Delete session
# ─────────────────────────────────────────
@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    try:
        await session_service.delete_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
    except Exception:
        pass  # Session may not exist in DB yet
    session_meta.pop(session_id, None)
    return JSONResponse({"deleted": session_id})


# ─────────────────────────────────────────
# Session chat history  ← NEW
# Returns the persisted messages for a session so the frontend
# can re-hydrate the chat after a page reload or app restart.
# ─────────────────────────────────────────
@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """
    Reads stored ADK events for a session and returns only the
    user-facing user/bot message pairs.

    Filtering rules (mirrors chatbot.py chat_stream):
      • role == "user"  → always included
      • agent event     → included only when NOT partial  (i.e. final response)
    """
    try:
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
    except Exception:
        return JSONResponse({"messages": []})

    if not session:
        return JSONResponse({"messages": []})

    messages = []
    for event in getattr(session, "events", None) or []:
        content = getattr(event, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        text_parts = [p.text for p in parts if getattr(p, "text", None)]
        if not text_parts:
            continue
        text = "".join(text_parts)

        role = getattr(content, "role", None)
        if role == "user":
            messages.append({"role": "user", "text": text})
        else:
            # Skip partial / streaming chunks; keep only final responses
            if not getattr(event, "partial", False):
                messages.append({"role": "bot", "text": text})

    return JSONResponse({"messages": messages})


# ─────────────────────────────────────────
# Streaming chat
# ─────────────────────────────────────────
@app.get("/chat/stream")
async def chat_stream_endpoint(user_input: str, session_id: str):
    # Auto-set name from first message (first 30 chars)
    if session_id in session_meta and session_meta[session_id].get("name") == "New Chat":
        session_meta[session_id]["name"] = user_input[:30].strip() + ("…" if len(user_input) > 30 else "")

    async def event_generator():
        async for chunk in chat_stream(user_input, session_id):
            # JSON-encode so \n inside chunks is safe for SSE framing
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
