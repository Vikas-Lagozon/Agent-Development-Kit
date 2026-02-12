import os
from google.adk.agents import Agent
from google.adk.sessions import DatabaseSessionService
from google.adk import Runner
from config import config

# -------------------------------------------------
# Ensure API key is used (NOT Vertex)
# -------------------------------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# -------------------------------------------------
# Create Agent
# -------------------------------------------------
SYSTEM_INSTRUCTION = """
You are a Market Intelligence Assistant.
Responsibilities:
- Answer business and market-related questions.
- Provide structured, professional responses.
- Be concise and data-driven.
- If unsure, clearly say more data is needed.
"""

intelligence_agent = Agent(
    name="market_intelligence_agent",
    model="gemini-2.0-flash",
    description="AI agent for market intelligence and analytics.",
    instruction=SYSTEM_INSTRUCTION,
)

# -------------------------------------------------
# Database Session Service with connection pooling disabled
# This helps prevent "another operation in progress" errors
# -------------------------------------------------
session_service = DatabaseSessionService(
    db_url=config.SQLALCHEMY_DATABASE_URI,
    connect_args={
        "server_settings": {
            "search_path": config.DB_SCHEMA
        }
    },
    pool_size=2,  # Limit pool size to avoid conflicts
    max_overflow=0  # No overflow connections
)

# -------------------------------------------------
# Runner
# -------------------------------------------------
runner = Runner(
    app_name="market_intelligence_app",
    agent=intelligence_agent,
    session_service=session_service
)

print("✅ Agent initialized successfully (API Key mode)")
print(f"Using schema: {config.DB_SCHEMA}")
print(f"Database URL: {config.SQLALCHEMY_DATABASE_URI}")
