const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const resetButton = document.getElementById("reset");

const modelBox = document.getElementById("model");
const usageBox = document.getElementById("usage");
const contextBox = document.getElementById("context");

function addMessage(role, content) {
    const emptyState = document.querySelector(".empty-state");
    if (emptyState) {
        emptyState.remove();
    }

    const div = document.createElement("div");
    div.className = `message ${role}`;

    const roleDiv = document.createElement("div");
    roleDiv.className = "role";
    roleDiv.textContent = role === "user" ? "You" : "Assistant";

    const contentDiv = document.createElement("div");

    if (role === "assistant") {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    div.appendChild(roleDiv);
    div.appendChild(contentDiv);
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function updateContext(data) {
    modelBox.textContent = data.model || "-";
    usageBox.textContent = JSON.stringify(data.usage, null, 2);
    contextBox.textContent = JSON.stringify(data.messages_sent_to_model, null, 2);
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    addMessage("user", message);
    messageInput.value = "";

    addMessage("assistant", "Thinking...");

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        const assistantMessages = chat.querySelectorAll(".assistant");
        const lastAssistantMessage = assistantMessages[assistantMessages.length - 1];
        lastAssistantMessage.querySelector("div:last-child").innerHTML = marked.parse(data.answer);

        updateContext(data);
    } catch (error) {
        const assistantMessages = chat.querySelectorAll(".assistant");
        const lastAssistantMessage = assistantMessages[assistantMessages.length - 1];
        lastAssistantMessage.querySelector("div:last-child").textContent =
            "Error calling the backend: " + error;
    }
});

resetButton.addEventListener("click", async () => {
    await fetch("/reset", { method: "POST" });
    chat.innerHTML = "";
    modelBox.textContent = "-";
    usageBox.textContent = "No request yet.";
    contextBox.textContent = "No context yet.";
});
