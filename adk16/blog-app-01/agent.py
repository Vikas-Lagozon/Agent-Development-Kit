# agent.py

import os
from config import config
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App

# -----------------------------
# Centralized Configuration
# -----------------------------
APP_NAME = "research_blog_app"
MODEL = "gemini-2.5-flash"

# Set Gemini API Key from config
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# ---------------------------------------------------
# 1️⃣ Research Agent
# ---------------------------------------------------
research_agent = Agent(
    name="research_agent",
    model=MODEL,
    description="Performs structured technical research.",
    instruction="""
You are a technical research expert.

Provide structured research notes about the given topic.

Rules:
- Bullet points
- Clear structure
- Technical precision
- No blog writing
- No intro or conclusion
Return only research notes.
"""
)

# ---------------------------------------------------
# 2️⃣ Blog Generator Agent
# ---------------------------------------------------
blog_agent = Agent(
    name="blog_generator_agent",
    model=MODEL,
    description="Converts research notes into a professional blog article.",
    instruction="""
You are a professional technical blog writer.

Convert the provided research notes into a complete blog article.

Requirements:
- Clear introduction
- Section headings
- Developer-focused tone
- Strong conclusion
- No emojis
- Paragraph format (not bullet-only)

Return only the final blog article.
"""
)

# ---------------------------------------------------
# 3️⃣ Root Controller Agent
# ---------------------------------------------------
root_agent = Agent(
    name="controller_agent",
    model=MODEL,
    description="Orchestrates research and blog generation workflow.",
    instruction="""
Workflow:
1. Send the topic to research_agent.
2. Take research output.
3. Send it to blog_generator_agent.
4. Return only the final blog article.
""",
    sub_agents=[research_agent, blog_agent],
)

# ---------------------------------------------------
# 4️⃣ Define App (Deployable Unit)
# ---------------------------------------------------
app = App(
    name=APP_NAME,
    root_agent=root_agent,
)

