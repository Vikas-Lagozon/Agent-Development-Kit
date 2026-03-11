from google.adk.agents.llm_agent import Agent
from google.adk.apps import App

report_agent = Agent(
    model='gemini-2.5-flash',
    name='greeter_agent',
    description='',
    instruction='',
)

app = App(
    name="agents",
    root_agent=report_agent,
    # Optionally include App-level features:
    # plugins, context_cache_config, resumability_config
)

