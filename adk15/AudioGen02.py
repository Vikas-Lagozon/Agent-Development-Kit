import os
import asyncio
from datetime import datetime
from google import genai
from google.genai import types
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.google_search_tool import google_search
from google.adk.tools import FunctionTool
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
import wave
from config import config

# ============================================================
# CONFIG
# ============================================================
APP_NAME = "Dynamic-Topic-Speech-Pipeline"
USER_ID = "user_001"
SESSION_ID = "session_001"
TEXT_MODEL = "gemini-2.5-flash"
TTS_MODEL = "gemini-2.5-flash-preview-tts"

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# ============================================================
# HELPER: Save PCM to WAV
# ============================================================
def save_wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# ============================================================
# TOOL: TTS GENERATION (NO DEFAULTS — REQUIRED PARAMS)
# ============================================================
async def generate_tts_tool(
    speech_text: str,
    topic_name: str,
    voice_name: str,
    language: str
) -> dict:

    client = genai.Client()

    print(f"\n🎤 Generating Speech Audio in '{language}' with voice '{voice_name}'...\n")

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=speech_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                ),
                language_code=language
            ),
        )
    )

    data = response.candidates[0].content.parts[0].inline_data.data

    topic_name_clean = "".join(c if c.isalnum() else "_" for c in topic_name.strip())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join("generated_speech", f"{topic_name_clean}_{timestamp}.wav")

    save_wave_file(filename, data)

    print(f"\n✅ Speech Audio Generated Successfully: {filename}\n")

    return {"status": "success", "filename": filename}


generate_tts = FunctionTool(func=generate_tts_tool)

# ============================================================
# AGENT 1 — RESEARCH
# ============================================================
research_agent = LlmAgent(
    name="deep_topic_research_agent",
    model=TEXT_MODEL,
    instruction="""
You are an expert researcher.

1. Perform extensive research using reliable sources.
2. Gather information from websites, news, reports, blogs, and statistics.
3. Produce 3000–4000 words.
4. Ensure factual accuracy.
5. Output ONLY the research content.
""",
    tools=[google_search]
)

# ============================================================
# AGENT 2 — SPEECH WRITER
# ============================================================
speech_agent = LlmAgent(
    name="speech_preparation_agent",
    model=TEXT_MODEL,
    instruction="""
You are a professional speechwriter.

Convert the research into a natural, engaging speech.
Output ONLY the speech text.
"""
)

# ============================================================
# AGENT 3 — TRANSLATION
# ============================================================
translation_agent = LlmAgent(
    name="translation_agent",
    model=TEXT_MODEL,
    instruction="""
You are a professional translator.

Translate the speech into the target language specified
in the user request.

Preserve natural spoken style.
Do not summarize or shorten.
Output ONLY the translated text.
"""
)

# ============================================================
# AGENT 4 — TTS CONTROLLER
# ============================================================
tts_agent = LlmAgent(
    name="tts_agent",
    model=TEXT_MODEL,
    instruction="""
You are a TTS controller.

You MUST call generate_tts with ALL required arguments:

- speech_text (translated speech)
- topic_name
- voice_name (exactly as specified in the user request)
- language (exactly as specified in the user request)

Do not change or invent parameter values.
""",
    tools=[generate_tts]
)

# ============================================================
# PIPELINE
# ============================================================
pipeline_agent = SequentialAgent(
    name="dynamic_topic_speech_pipeline",
    sub_agents=[
        research_agent,
        speech_agent,
        translation_agent,
        tts_agent
    ]
)

# ============================================================
# RUNNER
# ============================================================
async def main(topic_name: str, voice_name: str, language: str):

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    runner = Runner(
        agent=pipeline_agent,
        app_name=APP_NAME,
        session_service=session_service,
        artifact_service=artifact_service
    )

    # Inject runtime config into prompt
    user_prompt = f"""
Create a comprehensive research report on the topic: {topic_name}

Target translation language: {language}
TTS voice to use: {voice_name}

Instructions:
- Translate final speech into {language}
- Call generate_tts with voice_name="{voice_name}"
- Call generate_tts with language="{language}"
"""

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=user_prompt)]
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print("\n🧠 TEXT OUTPUT:\n", part.text)
                elif part.function_call:
                    print("\n🔧 TOOL CALL →", part.function_call.name)
                elif part.function_response:
                    print("\n✅ TOOL RESPONSE →", part.function_response.response)


# ============================================================
# EXAMPLE RUN
# ============================================================

asyncio.run(main("Indian Culture", voice_name="Achird", language="hi"))