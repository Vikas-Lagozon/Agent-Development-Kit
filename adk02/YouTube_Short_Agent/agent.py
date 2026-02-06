from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from dotenv import load_dotenv, find_dotenv

from .util import load_instructions_from_file

load_dotenv(find_dotenv())

MODEL = "gemini-2.5-pro"

# ==================================== Sub Agents ====================================

# --- Sub Agent 1: Script Writer ---
scriptwriter_agent = LlmAgent(
    name="ScriptWriterAgent",
    model=MODEL,
    # Loads instructions for professional, informative YouTube Shorts [cite: 1]
    instruction=load_instructions_from_file("scriptwriter_instruction.txt"),
    # Directly passing the function avoids the 'name' keyword error
    tools=[google_search], 
    output_key="generated_script",
)

# --- Sub Agent 2: Visualizer ---
visualizer_agent = LlmAgent(
    name="ShortVisualizerAgent",
    model=MODEL,
    # Loads instructions for visual planning and clarity [cite: 16, 18]
    instruction=load_instructions_from_file("visualizer_instruction.txt"),
    description="Generates visual concepts based on the provided script.",
    output_key="generated_visuals",
)

# --- Sub Agent 3: Formatter ---
formatter_agent = LlmAgent(
    name="ShortFormatterAgent",
    model=MODEL,
    instruction=(
        "Combine the script from state['generated_script'] "
        "and visual concepts from state['generated_visuals'] "
        "into a formatted YouTube short concept."
    ),
    description="Formats the script and visual concepts into a final YouTube short format.",
    output_key="final_short_concept",
)

# ==================================== Root Agent ====================================
# --- LLM Agent ---
youtube_short_agent = LlmAgent(
    name="YouTubeShortAgent",
    model=MODEL,
    instruction=f"""
You are a YouTube Short Content Creator Agent.

Workflow:
1. {scriptwriter_agent.name}
2. {visualizer_agent.name}
3. {formatter_agent.name}
""",
    tools=[
        AgentTool(agent=scriptwriter_agent),
        AgentTool(agent=visualizer_agent),
        AgentTool(agent=formatter_agent),
    ],
)

root_agent = youtube_short_agent

