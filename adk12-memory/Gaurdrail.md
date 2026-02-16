## **Gaurdrail**
```
User Message
    ↓
Before Model Callback
    ↓
LLM (Gemini) generates response
    ↓
After Model Callback
    ↓
(If model decides to call a tool)
    ↓
Before Tool Callback
    ↓
Tool Executes
    ↓
After Tool Callback
    ↓
Final Response
```

### **Before Model Callback**
🔹 Runs: BEFORE calling Gemini model
🔹 Purpose: Modify input to the LLM or block execution

### **After Model Callback**
🔹 Runs: AFTER model generates output
🔹 Purpose: Inspect or modify LLM output

### **Before Tool Callback**
🔹 Runs: BEFORE tool executes
🔹 Purpose: Modify tool arguments or block tool call

### **After Tool Callback**
🔹 Runs: AFTER tool execution
🔹 Purpose: Modify tool result before sending back to model

