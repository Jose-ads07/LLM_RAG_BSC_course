const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const resetButton = document.getElementById("reset");

const modelBox = document.getElementById("model");
const usageBox = document.getElementById("usage");
const contextBox = document.getElementById("context");
const conversationListBox = document.getElementById("conversation-list");

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

function clearEmptyState() {
    const emptyState = document.querySelector(".empty-state");
    if (emptyState) {
        emptyState.remove();
    }
}

function addMessage(role, content) {
    clearEmptyState();

    const div = document.createElement("div");
    div.className = "message " + role;

    const roleDiv = document.createElement("div");
    roleDiv.className = "role";
    roleDiv.textContent = role === "user" ? "You" : "Jai";

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

function showEmptyState() {
    chat.innerHTML = "";

    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = `
        <h3>Start a conversation</h3>
        <p>The assistant answer will appear here. The right panel shows the context and token usage.</p>
    `;

    chat.appendChild(emptyState);
}

function updateContext(data) {
    modelBox.textContent = data.model || "-";
    usageBox.textContent = JSON.stringify(data.usage, null, 2);
    contextBox.textContent = JSON.stringify(data.messages_sent_to_model, null, 2);
    renderConversationList(data.conversations || [], data.active_conversation_id);
}

function renderConversationList(conversations, activeConversationId) {
    conversationListBox.innerHTML = "";

    if (!conversations || conversations.length === 0) {
        conversationListBox.textContent = "No previous chats yet.";
        return;
    }

    for (const conversation of conversations) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "conversation-button";

        if (conversation.id === activeConversationId) {
            button.className += " active";
        }

        button.textContent = `${conversation.title} #${conversation.id}`;

        button.addEventListener("click", async function () {
            await selectConversation(conversation.id);
        });

        conversationListBox.appendChild(button);
    }
}

async function selectConversation(conversationId) {
    try {
        const response = await fetch(`/conversations/${conversationId}/select`, {
            method: "POST"
        });

        if (!response.ok) {
            throw new Error("Backend returned " + response.status);
        }

        const data = await response.json();

        renderSavedMessages(data.messages_sent_to_model);
        updateContext(data);

    } catch (error) {
        console.error("Could not select conversation:", error);
        alert("Could not load the selected chat.");
    }
}

function renderSavedMessages(messages) {
    chat.innerHTML = "";

    if (!messages || messages.length === 0) {
        showEmptyState();
        return;
    }

    for (const message of messages) {
        addMessage(message.role, message.content);
    }

    chat.scrollTop = chat.scrollHeight;
}

async function loadSavedState() {
    try {
        const response = await fetch("/state");

        if (!response.ok) {
            throw new Error("Backend returned " + response.status);
        }

        const data = await response.json();

        renderSavedMessages(data.messages_sent_to_model);
        updateContext(data);

    } catch (error) {
        console.error("Could not load saved state:", error);
        showEmptyState();
    }
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
    const response = await fetch("/conversations/new", {
        method: "POST"
    });

    if (!response.ok) {
        alert("Could not create a new chat.");
        return;
    }

    const data = await response.json();

    showEmptyState();
    updateContext(data);
});

loadSavedState();
