# main.py

import asyncio
from google.adk.runners import InMemoryRunner
from agent import app

# Create Runner
runner = InMemoryRunner(app=app)

async def main():
    try:
        topic = """
Explain the Purpose of App Class in Google ADK including:

- Centralized Configuration
- Lifecycle Management
- State Scope
- Unit of Deployment
- Define an App object
- Root Agent concept
"""

        response = await runner.run_debug(topic)

        print("\n📘 Generated Blog:\n")
        print(response)

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())

