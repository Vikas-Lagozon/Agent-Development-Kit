from google.adk.agents import LlmAgent
from google.adk.runners import Runner

from config import config
from agent_app.redis_session_service import RedisSessionService


session_service = RedisSessionService(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    ttl=config.REDIS_TTL,
)


agent = LlmAgent(
    name="RedisGeminiAgent",
    model="gemini-2.5-flash",
    description="Gemini agent with Redis-backed session persistence.",
    instruction="""You are a helpful assistant.
If the user asks you to remember something, store it in session.state.
If the user asks to recall something, check session.state.""",
)

# Expose root_agent as required by ADK
root_agent = agent

runner = Runner(
    app_name="agent_app",
    agent=root_agent,
    session_service=session_service,
)

app = runner.app
