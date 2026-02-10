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





# current structure
adk09/
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

# requred structure
adk09/
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
|     ├─ search_tool.py   # Instead of google_search I want to use duckduckgo search (which is free)
│     └─ query_tool.py   # Instead of big query i want to use postgressql( present into my local system)
│
├─ requirements.txt
└─ pq_query.sql


# Ollama
(venv) D:\Agent-Development-Kit\adk09>ollama list
NAME          ID              SIZE      MODIFIED
qwen3:1.7b    8f68893c685c    1.4 GB    5 minutes ago
qwen3:0.6b    7df6b6e09427    522 MB    5 days ago

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

give me the updated code of `agent.py`, `search_tool.py`, `query_tool.py`, and `pq_query.sql`.
Note: Please focus on the given task.
Caution: Do not try to add extra features which I did not say to implement.
Requried: Keep the given flow 
```
User Query
   ↓
LlmAgent (Ollama)
   ↓
Google Search Tool
   ↓
Extract growth % from snippets
   ↓
Compare with PostgresSQL Query sales growth
   ↓
Final Verdict (Beating / Lagging Market)
```


Postgres Password: abcd1234
