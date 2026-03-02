# app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from chatbot import chat_stream, session_service, APP_NAME, USER_ID
import uuid

app = FastAPI(title="Jarvis Chatbot")

# Templates & static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -----------------------------
# Home page
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    sessions_response = await session_service.list_sessions(
        app_name=APP_NAME,
        user_id=USER_ID
    )
    session_ids = [s.id for s in sessions_response.sessions] if sessions_response and sessions_response.sessions else []
    return templates.TemplateResponse("index.html", {"request": request, "sessions": session_ids})

# -----------------------------
# New chat endpoint
# -----------------------------
@app.post("/new_chat")
async def new_chat():
    new_session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=new_session_id
    )
    return JSONResponse({"session_id": new_session_id})

# -----------------------------
# Streaming chat endpoint
# -----------------------------
@app.get("/chat/stream")
async def chat_stream_endpoint(user_input: str, session_id: str):
    async def event_generator():
        async for chunk in chat_stream(user_input, session_id):
            # SSE format: "data: <text>\n\n"
            # Escape newlines inside the chunk to keep SSE format valid
            safe_chunk = chunk.replace("\n", " ")
            yield f"data: {safe_chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
