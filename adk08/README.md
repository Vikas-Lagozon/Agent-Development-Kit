adk08/
│
├─ .env
├─ service_account_key.json
├─ market_agent/
│  ├─ __init__.py
│  ├─ agent.py 
│  ├─ prompt.py
│  ├─ config.py
│  └─ tools/
│     ├─ __init__.py
|     ├─ google_search.py
│     └─ bigquery_tool.py
│
├─ requirements.txt
└─ bq_query.sql





adk08/
│
├─ .env
├─ service_account_key.json
├─ market_agent/
│  ├─ __init__.py
│  ├─ agent.py # Instead of using the gemini I want to use the Ollama model which is present into my local system
│  ├─ prompt.py
│  ├─ config.py
│  └─ tools/
│     ├─ __init__.py
|     ├─ google_search.py   # Instead of google_search I want to use duckduckgo search (which is free)
│     └─ bigquery_tool.py   # Instead of big query i want to use postgressql( present into my local system)
│
├─ requirements.txt
└─ bq_query.sql


# Ollama
(venv) D:\Agent-Development-Kit\adk08>ollama list
NAME          ID              SIZE      MODIFIED
qwen3:0.6b    7df6b6e09427    522 MB    5 days ago

(venv) D:\Agent-Development-Kit\adk08>

```
from langchain_ollama import ChatOllama

model = ChatOllama(
    model="qwen3:0.6b",
    temperature=0.5
)

query = "Hi, How are you?"

response = model.invoke(query)
print(response.content)
```
