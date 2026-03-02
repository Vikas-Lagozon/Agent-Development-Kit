chatbot_project/
│
├─ chatbot.py                # Core chatbot logic with streaming
├─ app.py                    # FastAPI backend server (SSE + multi-session)
├─ config.py                 # Configuration (Postgres, API key, etc.)
├─ .env                      # Environment variables (GOOGLE_API_KEY, DB creds)
│
├─ templates/
│   └─ index.html            # Frontend HTML with chat UI and session controls
│
├─ static/
│   ├─ style.css             # Chat UI styling
│   └─ script.js             # Frontend JS for streaming chat and session handling
│
└─ requirements.txt          # Python dependencies
