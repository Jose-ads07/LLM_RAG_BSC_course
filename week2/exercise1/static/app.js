const DEFAULT_SYSTEM_PROMPT = `You are a careful assistant that answers only from the uploaded document. If the document does not contain the answer, say that you do not know from the provided context.`;

const DEFAULT_TEMPLATE = `Use only the information in the context below to answer the question.
If the answer is not in the context, say that you do not know from the provided context.

Context:
---
{context}
---

Question: {user_input}`;

const state = {
  assistants: [],
  selectedAssistant: null,
  activeTab: "context",
};

const elements = {
  assistantSelect: document.querySelector("#assistantSelect"),
  assistantForm: document.querySelector("#assistantForm"),
  assistantName: document.querySelector("#assistantName"),
  systemPrompt: document.querySelector("#systemPrompt"),
  promptTemplate: document.querySelector("#promptTemplate"),
  uploadForm: document.querySelector("#uploadForm"),
  contextFile: document.querySelector("#contextFile"),
  contextStatus: document.querySelector("#contextStatus"),
  chatHistory: document.querySelector("#chatHistory"),
  chatForm: document.querySelector("#chatForm"),
  userInput: document.querySelector("#userInput"),
  clearChat: document.querySelector("#clearChat"),
  debugAssistantName: document.querySelector("#debugAssistantName"),
  tokenBadge: document.querySelector("#tokenBadge"),
  debugContent: document.querySelector("#debugContent"),
  toast: document.querySelector("#toast"),
  tabs: document.querySelectorAll(".tab"),
};

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => elements.toast.classList.remove("show"), 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail : payload;
    throw new Error(detail || "Request failed.");
  }
  return payload;
}

function debugData() {
  const assistant = state.selectedAssistant;
  return assistant?.last_debug || {
    assistant_name: assistant?.name || "",
    context_text: assistant?.context_text || "",
    filled_prompt: "",
    messages_sent: [],
    usage: {},
  };
}

function formatUsage(usage) {
  if (!usage || Object.keys(usage).length === 0) {
    return "No token usage yet.";
  }

  const orderedKeys = ["provider", "model", "prompt_tokens", "completion_tokens", "total_tokens", "note"];
  const lines = [];
  for (const key of orderedKeys) {
    if (usage[key] !== undefined) {
      lines.push(`${key}: ${usage[key]}`);
    }
  }
  for (const [key, value] of Object.entries(usage)) {
    if (!orderedKeys.includes(key)) {
      lines.push(`${key}: ${JSON.stringify(value)}`);
    }
  }
  return lines.join("\n");
}

function renderDebug() {
  const debug = debugData();
  const usage = debug.usage || {};
  elements.debugAssistantName.textContent = debug.assistant_name || state.selectedAssistant?.name || "No assistant";
  elements.tokenBadge.textContent = `prompt_tokens: ${usage.prompt_tokens ?? 0}`;

  const views = {
    context: `Assistant: ${debug.assistant_name || state.selectedAssistant?.name || "No assistant"}\n\nDocument:\n${debug.context_text || state.selectedAssistant?.context_text || "No document uploaded."}`,
    prompt: debug.filled_prompt || "No chat turn yet.",
    messages: debug.messages_sent?.length ? JSON.stringify(debug.messages_sent, null, 2) : "No model messages yet.",
    usage: formatUsage(usage),
  };

  elements.debugContent.textContent = views[state.activeTab] || "";
}

function renderHistory() {
  const history = state.selectedAssistant?.history || [];
  elements.chatHistory.innerHTML = "";

  if (!history.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No visible chat history yet.";
    elements.chatHistory.append(empty);
    return;
  }

  for (const message of history) {
    const bubble = document.createElement("article");
    bubble.className = `message ${message.role}`;

    const role = document.createElement("span");
    role.className = "message-role";
    role.textContent = message.role;

    const content = document.createElement("div");
    content.textContent = message.content;

    bubble.append(role, content);
    elements.chatHistory.append(bubble);
  }

  elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
}

function renderAssistantDetails() {
  const assistant = state.selectedAssistant;
  if (!assistant) {
    elements.contextStatus.textContent = "No context uploaded.";
    renderHistory();
    renderDebug();
    return;
  }

  elements.assistantName.value = assistant.name;
  elements.systemPrompt.value = assistant.system_prompt;
  elements.promptTemplate.value = assistant.prompt_template;
  elements.contextStatus.textContent = assistant.context_filename
    ? `Uploaded: ${assistant.context_filename}`
    : "No context uploaded.";
  renderHistory();
  renderDebug();
}

function renderAssistantSelect() {
  elements.assistantSelect.innerHTML = "";

  if (!state.assistants.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No saved assistants";
    elements.assistantSelect.append(option);
    return;
  }

  for (const assistant of state.assistants) {
    const option = document.createElement("option");
    option.value = assistant.id;
    option.textContent = assistant.name;
    option.selected = assistant.id === state.selectedAssistant?.id;
    elements.assistantSelect.append(option);
  }
}

async function loadAssistants(selectedId = state.selectedAssistant?.id) {
  state.assistants = await api("/api/assistants");
  const selected = state.assistants.find((assistant) => assistant.id === selectedId) || state.assistants[0] || null;
  state.selectedAssistant = selected;
  renderAssistantSelect();
  renderAssistantDetails();
}

function setBusy(form, busy) {
  for (const control of form.querySelectorAll("button, input, textarea")) {
    control.disabled = busy;
  }
}

elements.assistantForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(elements.assistantForm, true);
  try {
    const isUpdate = Boolean(state.selectedAssistant?.id);
    const assistant = await api(isUpdate ? `/api/assistants/${state.selectedAssistant.id}` : "/api/assistants", {
      method: isUpdate ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: elements.assistantName.value,
        system_prompt: elements.systemPrompt.value,
        prompt_template: elements.promptTemplate.value,
      }),
    });
    await loadAssistants(assistant.id);
    showToast("Assistant saved.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(elements.assistantForm, false);
  }
});

elements.assistantSelect.addEventListener("change", async () => {
  const assistantId = elements.assistantSelect.value;
  if (!assistantId) {
    state.selectedAssistant = null;
    renderAssistantDetails();
    return;
  }
  state.selectedAssistant = await api(`/api/assistants/${assistantId}`);
  renderAssistantSelect();
  renderAssistantDetails();
});

elements.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedAssistant) {
    showToast("Create or select an assistant first.");
    return;
  }

  const file = elements.contextFile.files[0];
  if (!file) {
    showToast("Choose a .txt file first.");
    return;
  }

  setBusy(elements.uploadForm, true);
  try {
    const body = new FormData();
    body.append("file", file);
    state.selectedAssistant = await api(`/api/assistants/${state.selectedAssistant.id}/context`, {
      method: "POST",
      body,
    });
    await loadAssistants(state.selectedAssistant.id);
    showToast("Context uploaded.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(elements.uploadForm, false);
  }
});

elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedAssistant) {
    showToast("Create or select an assistant first.");
    return;
  }

  const userInput = elements.userInput.value.trim();
  if (!userInput) {
    return;
  }

  setBusy(elements.chatForm, true);
  try {
    const result = await api(`/api/assistants/${state.selectedAssistant.id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: userInput }),
    });
    state.selectedAssistant = result.assistant;
    elements.userInput.value = "";
    renderAssistantSelect();
    renderAssistantDetails();
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(elements.chatForm, false);
    elements.userInput.focus();
  }
});

elements.clearChat.addEventListener("click", async () => {
  if (!state.selectedAssistant) {
    return;
  }
  try {
    state.selectedAssistant = await api(`/api/assistants/${state.selectedAssistant.id}/clear`, {
      method: "POST",
    });
    await loadAssistants(state.selectedAssistant.id);
    showToast("Chat cleared.");
  } catch (error) {
    showToast(error.message);
  }
});

for (const tab of elements.tabs) {
  tab.addEventListener("click", () => {
    state.activeTab = tab.dataset.tab;
    for (const item of elements.tabs) {
      item.classList.toggle("active", item === tab);
    }
    renderDebug();
  });
}

elements.assistantName.value = "";
elements.systemPrompt.value = DEFAULT_SYSTEM_PROMPT;
elements.promptTemplate.value = DEFAULT_TEMPLATE;

loadAssistants().catch((error) => showToast(error.message));
