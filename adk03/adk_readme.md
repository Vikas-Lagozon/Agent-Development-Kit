# ADK (Agent Development Kit)

## Interaction Interfaces

### CLI (`adk run <filename>`)
Directly runs agents in the command line for quick testing and execution.

### Web UI (`adk web`)
Spins up a new Angular-based UI for interacting with agents. Features multimodal capabilities, allowing interaction through text, voice, or video.

### API Server (`adk api_server`)
Exposes your agent as a REST API endpoint for integration with other services.

### Python API
Provides a programmatic way to invoke agents directly from Python code.

## ADK Services (`adk run`)

### Session
Manages the duration and state of a conversation between the user and agent.

### Runner (Event Processor)
Responsible for:
- Taking the input prompt
- Gathering all necessary services
- Invoking the parent agent
- Processing and streaming events asynchronously

### Event
Represents any atomic action that occurs within an agent. Events are streamed asynchronously from the Runner.

**Examples of events:**
- Input prompt passed to the runner
- Tool invocation
- Tool response received
- Any other atomic operation within the agent lifecycle

Events can be inspected individually for debugging and monitoring purposes.

### Services
Core services that support agent execution:
- **Session**: Maintains conversation state
- **Artifact**: Manages generated artifacts
- **Memory**: Handles agent memory and context
- And more...

### Execution Logic
The core components that drive agent behavior:
- Agent orchestration
- LLM invocation
- Tool execution
- Workflow management

### Storage
**Note:** Storage is not built into ADK core.

Available storage options:
- **MemorySession**: Temporary, in-memory storage (non-persistent)
- **Artifact Storage**: For persisting generated artifacts

## Getting Started

```bash
# Run an agent via CLI
adk run <filename>

# Launch the web interface
adk web

# Start the API server
adk api_server
```

## Architecture Overview

```
Input → Runner → Parent Agent → [Subagents] → Events (streamed) → Output
         ↓
    Services (Session, Memory, Artifacts, etc.)
```

---

For more information, please refer to the official ADK documentation.