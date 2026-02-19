from google.adk.agents import LlmAgent
from config import config
from agent_app.redis_session_service import RedisSessionService


# Initialize Redis session service
session_service = RedisSessionService(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    ttl=config.REDIS_TTL,
)


# Create the agent
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

print(f"✅ RedisGeminiAgent loaded with Redis persistence ({config.REDIS_HOST}:{config.REDIS_PORT})")

