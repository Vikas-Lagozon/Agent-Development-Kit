from google.adk.agents import LlmAgent
from google.adk.tools import google_search
# 1. Add this import
from google.adk.models.lite_llm import LiteLlm 

# 2. Wrap your model name in the LiteLlm class
MODEL = LiteLlm(model="ollama_chat/qwen3:0.6b")

# --- Specialist Agent: Idea Generator ---
idea_agent = LlmAgent(
    model=MODEL,
    name="IdeaAgent",
    tools=[google_search],
    description="Brainstorm creative and exciting weekend travel ideas based on user preferences.",
    instruction="""
    You are a creative travel planner. 
    Use the search tool to find unique weekend getaway ideas tailored to the user's interests and location.
    Be specific about why these locations fit the user's request.
    """,
    disallow_transfer_to_peers=True,
)

# --- Specialist Agent: Budget Refiner ---
refiner_agent = LlmAgent(
    model=MODEL,
    name="RefinerAgent",
    description="Filters travel ideas to ensure they fit within a specific budget.",
    instruction="""
    Review the trip ideas provided by the IdeaAgent. 
    Use your tools to estimate costs for travel and stay. 
    Respond ONLY with the ideas likely to cost under the provided budget for a full weekend. 
    If none seem to fit, say 'No suitable ideas found within budget.'
    """,
    tools=[google_search],
    disallow_transfer_to_peers=True,
)

# --- Root Agent: The Orchestrator ---
root_agent = LlmAgent(
    model=MODEL,
    name="PlannerAgent",
    instruction=f"""
    You are a Trip Planner, coordinating specialist agents.
    Your goal is to provide budget-friendly weekend trip ideas. For each user request:
        1. Use "{idea_agent.name}" to brainstorm ideas based on the user's request. 
        2. Use "{refiner_agent.name}" to filter those ideas against the user's budget.
        3. Present the final, refined list to the user clearly.
    """,
    sub_agents=[idea_agent, refiner_agent],
)

