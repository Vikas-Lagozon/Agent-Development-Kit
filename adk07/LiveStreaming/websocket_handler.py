import asyncio
import base64
import json
import logging
import traceback
from typing import Any, Dict

from google.genai import types
from google.genai.live import RunConfig

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------

ACTIVE_SESSIONS: Dict[str, "SessionState"] = {}

# ---------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------

def create_session(session: "SessionState") -> "SessionState":
    print(f"Voice: {CONFIG['generation_config']['speech_config']}")
    print(f"Modalities: {CONFIG['generation_config']['response_modalities']}")

    # Supported voices: Aoede, Charon, Fenrir, Kore, Puck
    voice_config = types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfigDict(
            voice_name=CONFIG["generation_config"]["speech_config"]
        )
    )

    speech_config = types.SpeechConfig(voice_config=voice_config)

    run_config = RunConfig(
        response_modalities=CONFIG["generation_config"]["response_modalities"],
        speech_config=speech_config,
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    session.events = session.runner.run_live(
        session=session.session,
        run_config=run_config,
    )

    ACTIVE_SESSIONS[session.session_id] = session
    return session


def get_session(session_id: str) -> "SessionState":
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise KeyError(f"Session not found: {session_id}")
    return session

# ---------------------------------------------------------------------
# Agent → Client
# ---------------------------------------------------------------------

async def handle_agent_responses(websocket: Any, session: "SessionState") -> None:
    try:
        full_text = ""

        async for event in session.events:
            logger.info(event)

            # --- Interruption ---
            if getattr(event, "interrupted", False):
                session.log_event_output("Interrupted event detected")
                await websocket.send(json.dumps({
                    "type": "interruption",
                    "data": "Response stream interrupted by user."
                }))
                continue

            if not event.content or not event.content.parts:
                logger.debug(
                    f"No content - turn_complete={getattr(event, 'turn_complete', False)}"
                )
                continue

            part = event.content.parts[0]

            # --- Tool call ---
            if part.function_call:
                await websocket.send(json.dumps({
                    "type": "tool_call",
                    "data": {
                        "name": part.function_call.name,
                        "args": part.function_call.args,
                    }
                }))
                continue

            # --- Tool response ---
            if part.function_response:
                await websocket.send(json.dumps({
                    "type": "tool_result",
                    "data": {
                        "name": part.function_response.name,
                        "output": part.function_response.response,
                    }
                }))
                continue

            # --- Text ---
            if part.text:
                full_text += part.text

                if not getattr(event, "partial", False):
                    await websocket.send(json.dumps({
                        "type": "text",
                        "data": full_text
                    }))
                    full_text = ""
                continue

            # --- Inline data (image / audio) ---
            inline_data = part.inline_data
            if inline_data:
                encoded = base64.b64encode(inline_data.data).decode("utf-8")

                if inline_data.mime_type.startswith("image/"):
                    await websocket.send(json.dumps({
                        "type": "image",
                        "data": f"data:{inline_data.mime_type};base64,{encoded}"
                    }))
                    continue

                if inline_data.mime_type.startswith("audio/pcm"):
                    await websocket.send(json.dumps({
                        "type": "audio",
                        "data": f"data:{inline_data.mime_type};base64,{encoded}"
                    }))
                    continue

            await asyncio.sleep(0.05)

    except Exception as e:
        logger.error(f"Error handling agent responses: {e}")
        logger.error(traceback.format_exc())

# ---------------------------------------------------------------------
# Client → Agent
# ---------------------------------------------------------------------

async def handle_client_messages(websocket: Any, session: "SessionState") -> None:
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "audio":
                logger.debug("Client -> Gemini: audio")
                session.live_request_queue.send_realtime(
                    types.Blob(
                        data=data.get("data"),
                        mime_type="audio/pcm",
                    )
                )

            elif msg_type == "image":
                logger.debug("Client -> Gemini: image")
                session.live_request_queue.send_realtime(
                    types.Blob(
                        data=data.get("data"),
                        mime_type="image/jpeg",
                    )
                )

            elif msg_type == "text":
                logger.debug("Client -> Gemini: text")
                session.live_request_queue.send_realtime(
                    types.Content(
                        role="user",
                        parts=[types.ContentPart(text=data.get("data"))],
                    )
                )

    except Exception as e:
        if "connection closed" in str(e).lower():
            logger.info("WebSocket connection closed by client.")
        else:
            logger.error(f"Error handling client messages: {e}")
            logger.error(traceback.format_exc())

