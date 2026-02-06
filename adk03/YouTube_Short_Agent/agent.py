from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search
from dotenv import load_dotenv, find_dotenv

from .util import load_instructions_from_file

load_dotenv(find_dotenv())

MODEL = "gemini-2.5-pro"

# ==================================== Sub Agents ====================================

# --- Sub Agent 1: Script Writer ---
scriptwriter_agent = LlmAgent(
    name="ScriptWriterAgent",
    model=MODEL,
    instruction=load_instructions_from_file("scriptwriter_instruction.txt"),
    tools=[google_search], 
    output_key="generated_script",
)

# --- Sub Agent 2: Visualizer ---
visualizer_agent = LlmAgent(
    name="ShortVisualizerAgent",
    model=MODEL,
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

youtube_short_agent = LoopAgent(
    name="YouTubeShortAgent",
    max_iterations=3,
    # Sub-agents must be a list of Agent instances, not AgentTools
    sub_agents=[
        scriptwriter_agent,
        visualizer_agent,
        formatter_agent,
    ],
    # 'instruction' is not permitted in LoopAgent; use 'description' instead
    description="A multi-agent loop that researches, writes, visualizes, and formats YouTube Shorts."
)


root_agent = youtube_short_agent



