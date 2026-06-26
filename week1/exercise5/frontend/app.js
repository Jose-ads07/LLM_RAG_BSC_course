const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const resetButton = document.getElementById("reset");

const modelBox = document.getElementById("model");
const usageBox = document.getElementById("usage");
const contextBox = document.getElementById("context");

function renderMarkdown(text) {
    if (window.marked && window.marked.parse) {
        return window.marked.parse(text);
    }

    return text
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\n", "<br>");
}

function addMessage(role, content) {
    const emptyState = document.querySelector(".empty-state");
    if (emptyState) {
        emptyState.remove();
    }

    const div = document.createElement("div");
    div.className = "message " + role;

    const roleDiv = document.createElement("div");
    roleDiv.className = "role";
    roleDiv.textContent = role === "user" ? "You" : "Assistant";

    const contentDiv = document.createElement("div");
    contentDiv.className = "content";

    if (role === "assistant") {
        contentDiv.innerHTML = renderMarkdown(content);
    } else {
        contentDiv.textContent = content;
    }

    div.appendChild(roleDiv);
    div.appendChild(contentDiv);
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;

    return contentDiv;
}

function updateContext(data) {
    modelBox.textContent = data.model || "-";
    usageBox.textContent = JSON.stringify(data.usage, null, 2);
    contextBox.textContent = JSON.stringify(data.messages_sent_to_model, null, 2);
}

function parseSSEBlock(block) {
    const lines = block.split("\n");
    let eventName = "message";
    let dataLines = [];

    for (const line of lines) {
        if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
        }

        if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
        }
    }

    const dataText = dataLines.join("");

    if (!dataText) {
        return null;
    }

    return {
        event: eventName,
        data: JSON.parse(dataText)
    };
}

async function sendStreamingMessage(message, assistantContent) {
    const response = await fetch("/chat/stream", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: message })
    });

    if (!response.ok) {
        throw new Error("Backend returned " + response.status);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    let streamedAnswer = "";

    while (true) {
        const result = await reader.read();

        if (result.done) {
            break;
        }

        buffer += decoder.decode(result.value, { stream: true });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop();

        for (const block of blocks) {
            const parsed = parseSSEBlock(block);

            if (!parsed) {
                continue;
            }

            if (parsed.event === "token") {
                streamedAnswer += parsed.data.token;
                assistantContent.innerHTML = renderMarkdown(streamedAnswer);
                chat.scrollTop = chat.scrollHeight;
            }

            if (parsed.event === "done") {
                updateContext(parsed.data);
            }

            if (parsed.event === "error") {
                assistantContent.textContent = "Streaming error: " + parsed.data.error;
            }
        }
    }
}

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    addMessage("user", message);
    messageInput.value = "";

    const assistantContent = addMessage("assistant", "Starting stream...");

    try {
        await sendStreamingMessage(message, assistantContent);
    } catch (error) {
        assistantContent.textContent = "Error calling the backend: " + error.message;
    }
});

resetButton.addEventListener("click", async function () {
    await fetch("/reset", { method: "POST" });

    chat.innerHTML = "";

    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = `
        <h3>Start a conversation</h3>
        <p>The assistant answer will appear here. The right panel shows the context and token usage.</p>
    `;

    chat.appendChild(emptyState);

    modelBox.textContent = "-";
    usageBox.textContent = "No request yet.";
    contextBox.textContent = "No context yet.";
});
