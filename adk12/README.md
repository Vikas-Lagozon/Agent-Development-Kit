# Redis Persistence with Google ADK Agent

## Fixed Issues
1. ✅ Changed `model_config` to `instruction` parameter
2. ✅ Added `app_name="agent_app"` to Runner
3. ✅ Updated model to `gemini-2.5-flash`
4. ✅ Explicitly disabled Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI = "0"`)

## Setup Instructions

### 1. Make sure Redis is running
```bash
# Start Redis server (if not already running)
redis-server
```

### 2. Set up your environment variables
Create a `.env` file in your project root:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Replace files in your project
Replace these files in `agent_app/` folder:
- `agent.py`
- `config.py` (in root directory)
- `redis_session_service.py`

### 4. Directory Structure
Your structure should look like:
```
redis_persistence/
├── .env
├── config.py
└── agent_app/
    ├── __init__.py
    ├── agent.py
    └── redis_session_service.py
```

### 5. Run the agent
```bash
adk web
```

## Testing Redis Persistence

Once the server is running (http://127.0.0.1:8000), test the persistence:

### Test 1: Store data
```
User: Remember that my favorite color is blue
```

### Test 2: Verify Redis storage
Open a new terminal and check Redis:
```bash
redis-cli -a myredispassword
> KEYS adk:session:*
> GET adk:session:<session_id_from_above>
```

### Test 3: Recall data in same session
```
User: What is my favorite color?
```

### Test 4: Test session persistence (refresh page)
1. Note the session ID from the URL
2. Refresh the browser page
3. The session should reload from Redis
4. Ask: "What is my favorite color?" - it should remember

## Key Changes Made

### agent.py
- **Model**: Changed from `gemini-2.0-flash` to `gemini-2.5-flash`
- **instruction**: Changed from nested `model_config.system_instruction` to direct `instruction` parameter
- **Runner**: Added `app_name="agent_app"` parameter (required by ADK)

### config.py
- **Vertex AI**: Explicitly set to `"0"` to ensure it uses Google AI API directly

## Troubleshooting

### If you get "connection refused" to Redis:
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start it:
redis-server
```

### If you get authentication errors:
Make sure your `.env` file has a valid `GOOGLE_API_KEY`

### If sessions are not persisting:
1. Check Redis is running: `redis-cli -a myredispassword ping`
2. Check TTL (default 3600 seconds = 1 hour)
3. Monitor Redis: `redis-cli -a myredispassword MONITOR`

