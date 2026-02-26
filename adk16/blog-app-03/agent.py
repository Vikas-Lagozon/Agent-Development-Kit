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

Provide structured research notes about the given topic covering ALL of these sections:

1. HISTORY & ORIGIN
   - When and how it started
   - Key milestones and evolution timeline

2. PAST IMPACT
   - How it changed the landscape when it emerged
   - Early adoption and challenges

3. PRESENT CONDITIONS
   - Current state, major players, and usage
   - Latest developments and trends

4. FUTURE SCOPE
   - Predictions, roadmap, and upcoming advancements
   - Potential disruptions and opportunities

5. PROS & CONS
   - Clear advantages with reasoning
   - Clear limitations, risks, or concerns

Rules:
- Bullet points under each section
- Technical precision
- No blog writing or narrative prose
- No intro or conclusion paragraphs
Return only the structured research notes with the 5 sections above.
"""
)

# ---------------------------------------------------
# 2️⃣ Blog Generator Agent
# ---------------------------------------------------
blog_agent = Agent(
    name="blog_generator_agent",
    model=MODEL,
    description="Converts research notes into a structured professional blog article.",
    instruction="""
You are a professional technical blog writer.

Convert the provided research notes into a complete, well-structured blog article.

MANDATORY STRUCTURE (use these exact ## headings):
## Introduction
## History and Origin
## Past Impact
## Present Conditions
## Future Scope
## Pros and Cons
## Conclusion

WORD COUNT REQUIREMENT:
- Total blog MUST be between 1500 and 2000 words.
- Distribute words roughly evenly across sections.
- If a draft is under 1500 words, expand each section with more detail and examples.
- If over 2000 words, tighten the language without removing sections.

WRITING RULES:
- Developer and tech-practitioner audience
- Paragraph format (no bullet-only sections — convert bullets to flowing prose)
- Use sub-headings inside sections only if needed for clarity
- Strong, specific opening paragraph that hooks the reader
- Concrete examples and real-world references where applicable
- Pros and Cons section may use a short structured list for readability
- Strong conclusion that summarizes key takeaways and future outlook
- No emojis
- No filler phrases like "In conclusion," or "To summarize,"

Return ONLY the final blog article. No preamble, no word count notes, no meta-commentary.
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
1. Send the topic to research_agent to get structured research notes.
2. Pass the complete research notes to blog_generator_agent.
3. Return only the final blog article produced by blog_generator_agent. Nothing else.
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

