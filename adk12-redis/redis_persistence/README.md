# 🔴 REDIS PERSISTENCE FIX - COMPLETE SOLUTION

## 🚨 THE PROBLEM
Your ADK was using **local SQLite storage** instead of Redis because `adk web` creates its own session service by default, ignoring your custom `RedisSessionService`.

**Evidence from logs:**
```
2026-02-13 12:49:21,227 - INFO - local_storage.py:59 - Creating local session service at D:\Agent-Development-Kit\adk12\redis_persistence\agent_app\.adk\session.db
```

## ✅ THE SOLUTION

You have **TWO options** to fix this:

---

### **Option 1: Use Custom Server Script (RECOMMENDED)**

Instead of running `adk web`, use the custom server script that forces Redis usage.

#### **Setup:**

1. **Place these files in your project:**
   - `run_server.py` (in root directory)
   - `agent.py` (in agent_app/ directory)
   - `redis_session_service.py` (in agent_app/ directory)
   - `config.py` (in root directory)

2. **Project structure:**
```
redis_persistence/
├── .env
├── config.py
├── run_server.py          # ← NEW: Custom server
├── test_redis.py          # ← NEW: Test script
├── chat_history.py
└── agent_app/
    ├── __init__.py
    ├── agent.py
    └── redis_session_service.py
```

3. **Run the server:**
```bash
# Instead of 'adk web', run:
python run_server.py
```

4. **Access at:** http://127.0.0.1:8000

---

### **Option 2: Fix ADK Web Configuration (Advanced)**

The ADK web command looks for a `session_service` variable in your agent module.

#### **Updated agent.py:**
```python
from google.adk.agents import LlmAgent
from config import config
from agent_app.redis_session_service import RedisSessionService

# Create session service (MUST be module-level variable)
session_service = RedisSessionService(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    ttl=config.REDIS_TTL,
)

agent = LlmAgent(
    name="RedisGeminiAgent",
    model="gemini-2.5-flash",
    description="Gemini agent with Redis-backed session persistence.",
    instruction="""You are a helpful assistant.
If the user asks you to remember something, store it in session.state.
If the user asks to recall something, check session.state.""",
)

root_agent = agent
```

Then run with environment variable:
```bash
export ADK_SESSION_SERVICE=agent_app.agent.session_service
adk web
```

---

## 🧪 TESTING THE FIX

### **Step 1: Test Redis Connection**
```bash
python test_redis.py
```

Expected output:
```
🧪 Testing Redis Session Service...
1️⃣ Testing Redis connection...
   ✅ Redis connection successful
...
✅ All tests passed!
```

### **Step 2: Start Server**
```bash
python run_server.py
```

Expected output:
```
🚀 Starting ADK Server with Redis Session Persistence...
📡 Redis: localhost:6379
⏰ Session TTL: 3600 seconds

Server running at: http://127.0.0.1:8000
```

### **Step 3: Chat with Agent**
1. Open http://127.0.0.1:8000
2. Send message: "Remember my favorite color is blue"
3. Send message: "What's my favorite color?"

### **Step 4: Check Redis**
```bash
python chat_history.py
```

Expected output:
```
✅ Connected to Redis successfully!
📊 Found 1 session(s)

🔑 Session Key: adk:session:xxxxx
Session ID: xxxxx

💬 Chat History:
1. [USER]
Remember my favorite color is blue
2. [ASSISTANT]
Okay, I've stored that...
```

---

## 🔍 DEBUGGING

### **If sessions are still not in Redis:**

1. **Check if Redis is running:**
```bash
redis-cli -a myredispassword ping
# Should return: PONG
```

2. **Monitor Redis in real-time:**
```bash
# In one terminal:
redis-cli -a myredispassword MONITOR

# In another terminal:
python run_server.py
# Then chat with the agent
```

3. **Check which session service is being used:**
Look for these log lines when starting the server:
```
# ❌ BAD (using SQLite):
INFO - local_storage.py:59 - Creating local session service at .adk/session.db

# ✅ GOOD (using Redis):
🚀 Starting ADK Server with Redis Session Persistence...
```

---

## 📝 KEY FILES EXPLAINED

### **run_server.py**
- Custom server that **forces** Redis usage
- Bypasses ADK's default session service
- Direct control over the FastAPI app

### **test_redis.py**
- Tests Redis connection
- Creates/updates/deletes test sessions
- Verifies data is actually stored in Redis

### **chat_history.py**
- Views all session data from Redis
- Shows conversation history
- Useful for debugging

---

## ⚡ QUICK START COMMANDS

```bash
# 1. Test Redis
python test_redis.py

# 2. Start server (USE THIS INSTEAD OF 'adk web')
python run_server.py

# 3. Check session history
python chat_history.py
```

---

## 🎯 WHY THIS WORKS

**The Problem:**
- `adk web` auto-creates a local SQLite session service
- Your `RedisSessionService` was defined but never used
- The `Runner` in `agent.py` wasn't being picked up by `adk web`

**The Solution:**
- `run_server.py` creates the `Runner` with your `RedisSessionService`
- Runs uvicorn directly with the configured FastAPI app
- Complete control over session service initialization

**Alternative (Option 2):**
- Export `session_service` as a module-level variable
- ADK web can discover and use it (if configured correctly)
- Requires setting `ADK_SESSION_SERVICE` environment variable

---

## 🆘 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| "No sessions found in Redis" | Use `run_server.py` instead of `adk web` |
| "Connection refused" | Start Redis: `redis-server` |
| "Authentication failed" | Check password in `config.py` |
| Sessions expire too fast | Increase `REDIS_TTL` in `config.py` |
| Can't see chat history | Run `python chat_history.py` |

---

## ✅ SUCCESS CHECKLIST

- [ ] Redis is running (`redis-cli ping`)
- [ ] `.env` has `GOOGLE_API_KEY`
- [ ] Run `python test_redis.py` - all tests pass
- [ ] Run `python run_server.py` (not `adk web`)
- [ ] Chat with agent at http://127.0.0.1:8000
- [ ] Run `python chat_history.py` - see your messages
- [ ] Refresh browser - conversation persists!

**If all checked, Redis persistence is working! 🎉**
