let currentSession = document.getElementById("session-select").value;

// Switch session
document.getElementById("session-select").addEventListener("change", (e) => {
    currentSession = e.target.value;
    document.getElementById("chat-box").innerHTML = ""; // Clear messages for selected session
});

// New chat
document.getElementById("new-chat-btn").addEventListener("click", async () => {
    const res = await fetch("/new_chat", { method: "POST" });
    const data = await res.json();
    currentSession = data.session_id;

    // Add to dropdown
    const option = document.createElement("option");
    option.value = currentSession;
    option.text = currentSession;
    document.getElementById("session-select").appendChild(option);
    document.getElementById("session-select").value = currentSession;

    document.getElementById("chat-box").innerHTML = ""; // clear messages
});

// Chat form submission
const form = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;

    // Show user message
    const userMsgDiv = document.createElement("div");
    userMsgDiv.classList.add("chat-message", "user");
    userMsgDiv.innerText = message;
    chatBox.appendChild(userMsgDiv);
    userInput.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // Streaming via SSE
    const formData = new URLSearchParams();
    formData.append("user_input", message);
    formData.append("session_id", currentSession);

    const eventSource = new EventSource(`/chat/stream?${formData.toString()}`);

    const botMsgDiv = document.createElement("div");
    botMsgDiv.classList.add("chat-message", "bot");
    chatBox.appendChild(botMsgDiv);

    eventSource.onmessage = (event) => {
        botMsgDiv.innerText += event.data; // append token
        chatBox.scrollTop = chatBox.scrollHeight;
    };

    eventSource.onerror = () => {
        eventSource.close();
    };
});

