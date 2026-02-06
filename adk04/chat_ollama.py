from langchain_ollama import ChatOllama

model = ChatOllama(
    model="qwen3:0.6b",
    temperature=0.5
)

query = "Hi, How are you?"

response = model.invoke(query)
print(response.content)
