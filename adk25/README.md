# Redis Chatbot with Google ADK

A simple chatbot built with the **Google Agent Development Kit (ADK)** that persists conversation sessions in **Redis**. The chatbot maintains full conversation context across restarts using a custom `RedisSessionService`.

---

## Features

- Interactive command-line chatbot
- Conversation history stored in Redis for persistent, resumable sessions
- Custom `RedisSessionService` implementing ADK's `BaseSessionService`
- Session state delta tracking via `append_event`
- Uses **Gemini** models via the Google Generative Language API

---

## Project Structure

```
.
├── RedisChatbot.py                 # Main chatbot script and interactive loop
├── RedisDatabaseSessionService.py  # Custom Redis-backed session service
├── config.py                       # Environment config (API keys, DB, GCS, models)
├── requirements.txt
└── README.md
```

---

## Requirements

- Python 3.11+
- Docker (for Redis)
- Google Cloud account with **Generative Language API** enabled
- A valid `.env` file (see Configuration below)

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd <repo-directory>
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Required
GOOGLE_API_KEY=your_google_api_key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
BUCKET_NAME=your_gcs_bucket_name

# Models (optional, defaults shown)
MODEL=gemini-2.5-flash
RESEARCH_MODEL=gemini-2.0-flash

# PostgreSQL (optional)
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=
DB_SCHEMA=market_intelligence

# BigQuery (optional)
BQ_PROJECT_ID=your_project_id
BQ_DATASET=your_dataset
SERVICE_ACCOUNT_FILE=/path/to/service_account.json
```

> **Note:** `GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, and `BUCKET_NAME` are required. The app will raise a `ValueError` on startup if any of these are missing.

---

## Running Redis via Docker

### 1. Start the Redis container

```bash
docker pull redis:latest
docker run -d -p 6379:6379 --name redis_chatbot redis:latest
```

### 2. Verify it's running

```bash
docker ps
# You should see redis_chatbot running on port 6379
```

### 3. Test the connection

```bash
redis-cli ping
# Expected output: PONG
```

The app connects using:
```python
redis.from_url("redis://localhost:6379", decode_responses=True)
```

---

## Running the Chatbot

```bash
python RedisChatbot.py
```

On first run, a new Redis session is created. On subsequent runs, the existing session is resumed automatically.

```
=== ChatBot Interactive Session ===
Type 'exit' to quit.

Resuming existing Redis session: session_001
You: Hi!
ChatAgent: Hello! How can I help you today?
You: Suggest a fun weekend activity.
ChatAgent: You could try hiking, visiting a local museum, or experimenting with a new recipe at home!
You: exit
Ending chat session.
```

Type `exit` or `quit` to end the session.

---

## How Session Persistence Works

The `RedisSessionService` stores session data in two Redis keys per session:

| Key | Type | Contents |
|-----|------|----------|
| `session:{id}:meta` | Hash | `app_name`, `user_id`, `state` (JSON) |
| `session:{id}:events` | List | Serialized ADK `Event` objects (append-only) |

On each `append_event` call, any `state_delta` from the event is merged into the session's stored state. On `get_session`, all events are deserialized and returned, giving the ADK runner full conversation context.

---

## Customization

- **Change the session**: Update `SESSION_ID` in `RedisChatbot.py` to start a fresh conversation thread.
- **Change the model**: Set `MODEL` in your `.env` file (e.g., `gemini-2.0-flash`).
- **Adjust the agent**: Modify the `instruction` field in the `LlmAgent` constructor to change the bot's persona or behavior.

---

## Troubleshooting

**Redis connection refused**
- Confirm the Docker container is running: `docker ps`
- Ensure port `6379` is not blocked by a firewall
- Test with `redis-cli ping` — should return `PONG`

**Google API authentication error**
- Verify your `GOOGLE_API_KEY` is valid and has Generative Language API access enabled
- Confirm `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service account JSON file

**`ValueError` on startup**
- Check that `GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, and `BUCKET_NAME` are all set in your `.env` file

---

## License

MIT License