# Travel Agent ADK

Multi-agent system using Google ADK, LiteLLM, and Ollama for travel planning.

## File Structure

```
D:\ADK\
├── travel_agent\
│   ├── .env            # Google Search credentials
│   ├── __init__.py     # Package marker
│   ├── adk.yaml        # Entrypoint: agent:root_agent
│   └── agent.py        # Multi-agent orchestration
└── venv\               # Python 3.9-3.12
```

## Prerequisites

- **Ollama**: Running locally with `qwen3:0.6b`
- **Extensions**: `pip install "google-adk[extensions]"`

## Setup

### 1. Environment Variables

**Windows CMD:**
```cmd
set OLLAMA_API_BASE=http://localhost:11434
```

**PowerShell:**
```powershell
$env:OLLAMA_API_BASE="http://localhost:11434"
```

### 2. Google Search Configuration

Create `D:\ADK\travel_agent\.env`:
```env
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_search_engine_id
```

## Execution

From `D:\ADK`:
```bash
adk web .
```

## Stack

- **Orchestration**: Google ADK (Planner/Specialist)
- **LLM Proxy**: LiteLLM (`ollama_chat/`)
- **Model**: Qwen 3 (0.6B)
- **Tools**: Google Search

