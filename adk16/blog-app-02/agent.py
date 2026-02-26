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
    description="Performs detailed technical research.",
    instruction="""
You are a highly experienced technical research expert.

Given a topic, conduct thorough research and create structured research notes. 
Structure your notes into the following five sections:

1. Introduction: Provide context and background of the topic.
2. Key Concepts: Explain the essential terms, ideas, or technologies.
3. Current Trends: Highlight recent developments and innovations.
4. Challenges & Solutions: Identify common issues and ways to address them.
5. Summary & Insights: Conclude with actionable insights and key takeaways.

Be precise, comprehensive, and professional. Include examples or explanations when necessary. 
Keep the notes clear, logical, and ready for a professional blog writer to use directly.
"""
)

# ---------------------------------------------------
# 2️⃣ Blog Generator Agent
# ---------------------------------------------------
blog_agent = Agent(
    name="blog_generator_agent",
    model=MODEL,
    description="Transforms research notes into a professional blog article.",
    instruction="""
You are a professional technical blog writer with over 20 years of experience.

Your task is to convert the provided research notes into a polished, professional blog article.

Requirements:
- Decide the most suitable sub-topics based on the research notes.
- Each sub-topic should be clearly titled and contain 2-5 detailed points.
- Explain concepts deeply but clearly, making the content accessible to readers.
- Use a professional tone suitable for a technical blog.
- Include examples, analogies, or actionable insights where relevant.
- The article should be long enough to reflect a professional blog post; avoid overly brief explanations.
- Return ONLY the complete blog article. No introductions, summaries, or meta-commentary.

Focus on producing content that a professional blog writer would publish.
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
1. Send the user's topic to research_agent to get detailed research notes.
2. Provide the complete research notes to blog_generator_agent.
3. Return ONLY the final professional blog article produced by blog_generator_agent.
"""
,
    sub_agents=[research_agent, blog_agent],
)

# ---------------------------------------------------
# 4️⃣ Define App (Deployable Unit)
# ---------------------------------------------------
app = App(
    name=APP_NAME,
    root_agent=root_agent,
)