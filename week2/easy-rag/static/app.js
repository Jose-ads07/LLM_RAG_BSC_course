const DEFAULT_SYSTEM_PROMPT = `You are a careful assistant that answers only from the uploaded documents. If the documents do not contain the answer, say that you do not know from the provided context.`;

const DEFAULT_TEMPLATE = `Use only the information in the context below to answer the question.
If the answer is not in the context, say that you do not know from the provided context.

Context:
---
{context}
---

Question: {user_input}`;

const DEFAULTS = {
  retrieval_top_k: 4,
  retrieval_threshold: 0.4,
  chunk_strategy: "chars",
  chunk_size: 800,
  chunk_overlap: 100,
  section_level: 2,
};

const state = {
  assistants: [],
  selectedAssistant: null,
  activeTab: "documents",
  setupVisible: true,
  debugVisible: true,
};

const elements = {
  appShell: document.querySelector("#appShell"),
  topAssistantName: document.querySelector("#topAssistantName"),
  modelName: document.querySelector("#modelName"),
  appStatus: document.querySelector("#appStatus"),
  documentsMetric: document.querySelector("#documentsMetric"),
  chunksMetric: document.querySelector("#chunksMetric"),
  promptTokensMetric: document.querySelector("#promptTokensMetric"),
  completionTokensMetric: document.querySelector("#completionTokensMetric"),
  retrievedChunksMetric: document.querySelector("#retrievedChunksMetric"),
  toggleSetup: document.querySelector("#toggleSetup"),
  toggleDebug: document.querySelector("#toggleDebug"),
  assistantSelect: document.querySelector("#assistantSelect"),
  assistantForm: document.querySelector("#assistantForm"),
  assistantName: document.querySelector("#assistantName"),
  systemPrompt: document.querySelector("#systemPrompt"),
  promptTemplate: document.querySelector("#promptTemplate"),
  retrievalTopK: document.querySelector("#retrievalTopK"),
  retrievalThreshold: document.querySelector("#retrievalThreshold"),
  chunkStrategy: document.querySelector("#chunkStrategy"),
  chunkSize: document.querySelector("#chunkSize"),
  chunkOverlap: document.querySelector("#chunkOverlap"),
  sectionLevel: document.querySelector("#sectionLevel"),
  uploadForm: document.querySelector("#uploadForm"),
  dropZone: document.querySelector("#dropZone"),
  contextFile: document.querySelector("#contextFile"),
  contextStatus: document.querySelector("#contextStatus"),
  selectedFiles: document.querySelector("#selectedFiles"),
  uploadProgress: document.querySelector("#uploadProgress"),
  documentsList: document.querySelector("#documentsList"),
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

function numberValue(input, fallback) {
  const value = Number(input.value);
  return Number.isFinite(value) ? value : fallback;
}

function assistantPayload() {
  return {
    name: elements.assistantName.value,
    system_prompt: elements.systemPrompt.value,
    prompt_template: elements.promptTemplate.value,
    retrieval_top_k: numberValue(elements.retrievalTopK, DEFAULTS.retrieval_top_k),
    retrieval_threshold: numberValue(elements.retrievalThreshold, DEFAULTS.retrieval_threshold),
    chunk_strategy: elements.chunkStrategy.value || DEFAULTS.chunk_strategy,
    chunk_size: numberValue(elements.chunkSize, DEFAULTS.chunk_size),
    chunk_overlap: numberValue(elements.chunkOverlap, DEFAULTS.chunk_overlap),
    section_level: numberValue(elements.sectionLevel, DEFAULTS.section_level),
  };
}

function debugData() {
  const assistant = state.selectedAssistant;
  return assistant?.last_debug || {
    assistant_name: assistant?.name || "",
    collection_name: assistant?.collection_name || "",
    documents: assistant?.documents || [],
    context_text: "",
    retrieved_chunks: [],
    retrieval: {
      top_k: assistant?.retrieval_top_k || DEFAULTS.retrieval_top_k,
      threshold: assistant?.retrieval_threshold ?? DEFAULTS.retrieval_threshold,
    },
    filled_prompt: "",
    messages_sent: [],
    usage: {},
  };
}

function createEl(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined) {
    element.textContent = text;
  }
  return element;
}

function appendChildren(parent, children) {
  for (const child of children) {
    if (child) {
      parent.append(child);
    }
  }
  return parent;
}

function compactNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : "n/a";
}

function fileSizeLabel(bytes) {
  if (!Number.isFinite(bytes)) {
    return "";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function timeLabel(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return "now";
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function dateLabel(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) {
    return "just now";
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function similarityClass(value) {
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return "unknown";
  }
  if (score > 0.8) {
    return "green";
  }
  if (score > 0.6) {
    return "yellow";
  }
  if (score > 0.4) {
    return "orange";
  }
  return "red";
}

function modelLabel() {
  const usage = debugData().usage || {};
  if (usage.model) {
    return usage.model;
  }
  if (usage.provider === "local-demo" || usage.provider === "retrieval-gate") {
    return "demo mode";
  }
  return "qwen3:1.7b";
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

function extractContextPreviews(context) {
  if (!context) {
    return new Map();
  }

  const previews = new Map();
  const blocks = context.split(/\n\n(?=\[)/);
  for (const block of blocks) {
    const lines = block.split("\n");
    const header = lines.shift() || "";
    const title = header.match(/^\[([^|]+?)\s*\|/)?.[1]?.trim();
    const chunk = header.match(/\|\s*chunk\s+([^|]+?)\s*\|/)?.[1]?.trim();
    const similarity = header.match(/\|\s*similarity\s+([^\]]+)/)?.[1]?.trim();
    const preview = lines.join("\n").trim();
    if (title && chunk && preview) {
      previews.set(`${title}|${chunk}`, { preview, similarity });
    }
  }
  return previews;
}

function renderStatusMetrics() {
  const assistant = state.selectedAssistant;
  const debug = debugData();
  const usage = debug.usage || {};
  const docs = assistant?.document_count || assistant?.documents?.length || 0;
  const chunks = assistant?.chunk_count || 0;
  const retrieved = debug.retrieved_chunks?.length || 0;

  elements.topAssistantName.textContent = assistant?.name || "No assistant";
  elements.modelName.textContent = modelLabel();
  elements.documentsMetric.textContent = String(docs);
  elements.chunksMetric.textContent = String(chunks);
  elements.promptTokensMetric.textContent = usage.prompt_tokens ?? 0;
  elements.completionTokensMetric.textContent = usage.completion_tokens ?? 0;
  elements.retrievedChunksMetric.textContent = retrieved;
  elements.tokenBadge.textContent = `prompt_tokens: ${usage.prompt_tokens ?? 0}`;
  elements.appStatus.textContent = assistant ? `${debug.collection_name || assistant.collection_name || "Collection ready"}` : "Ready";
}

function renderCodeBlock(text, emptyText = "No data yet.") {
  const pre = createEl("pre", "code-block");
  pre.textContent = text || emptyText;
  return pre;
}

function renderDebugDocuments(documents) {
  const wrap = createEl("div", "inspector-list");
  if (!documents?.length) {
    wrap.append(createEl("p", "empty-copy", "No documents uploaded."));
    return wrap;
  }

  for (const document of documents) {
    wrap.append(renderDocumentCard(document, { compact: true }));
  }
  return wrap;
}

function renderRetrievedCards(chunks, context) {
  const wrap = createEl("div", "inspector-list");
  if (!chunks?.length) {
    wrap.append(createEl("p", "empty-copy", "No retrieved chunks for the latest turn."));
    return wrap;
  }

  const previews = extractContextPreviews(context);
  for (const chunk of chunks) {
    const card = createEl("article", "retrieved-card slide-in");
    const key = `${chunk.title || chunk.filename}|${chunk.chunk_number}`;
    const preview = previews.get(key)?.preview || "Preview available in the Filled Prompt tab.";

    const header = createEl("div", "retrieved-header");
    const title = createEl("strong", "", chunk.title || chunk.filename || "Source document");
    const badge = createEl("span", `similarity-badge ${similarityClass(chunk.similarity)}`, compactNumber(chunk.similarity));
    header.append(title, badge);

    const meta = createEl("div", "retrieved-meta", `Chunk ${chunk.chunk_number}`);
    const body = createEl("p", "retrieved-preview", preview.length > 260 ? `${preview.slice(0, 260)}...` : preview);
    const links = createEl("div", "document-links");
    const original = createEl("a", "", "Original");
    original.href = chunk.doc_url || "#";
    original.target = "_blank";
    original.rel = "noreferrer";
    const markdown = createEl("a", "", "Markdown");
    markdown.href = chunk.markdown_url || "#";
    markdown.target = "_blank";
    markdown.rel = "noreferrer";
    links.append(original, markdown);

    appendChildren(card, [header, meta, body, links]);
    wrap.append(card);
  }
  return wrap;
}

function renderUsageCards(usage, retrievedCount) {
  const grid = createEl("div", "usage-grid");
  const entries = [
    ["Prompt Tokens", usage?.prompt_tokens ?? 0],
    ["Completion Tokens", usage?.completion_tokens ?? 0],
    ["Total Tokens", usage?.total_tokens ?? 0],
    ["Retrieved Chunks", retrievedCount],
    ["Provider", usage?.provider || "n/a"],
    ["Latency", usage?.latency || "n/a"],
  ];

  for (const [label, value] of entries) {
    const card = createEl("div", "usage-card");
    card.append(createEl("span", "", label), createEl("strong", "", String(value)));
    grid.append(card);
  }

  if (usage?.note) {
    const note = createEl("p", "usage-note", usage.note);
    const container = createEl("div", "usage-stack");
    container.append(grid, note);
    return container;
  }
  return grid;
}

function renderDebug() {
  const debug = debugData();
  const usage = debug.usage || {};
  const documents = debug.documents || state.selectedAssistant?.documents || [];
  const retrieved = debug.retrieved_chunks || [];

  elements.debugAssistantName.textContent = debug.assistant_name || state.selectedAssistant?.name || "No assistant";
  renderStatusMetrics();
  elements.debugContent.innerHTML = "";

  const views = {
    documents: () => renderDebugDocuments(documents),
    retrieved: () => renderRetrievedCards(retrieved, debug.context_text),
    prompt: () => renderCodeBlock(debug.filled_prompt, "No chat turn yet."),
    messages: () => renderCodeBlock(debug.messages_sent?.length ? JSON.stringify(debug.messages_sent, null, 2) : "", "No model messages yet."),
    usage: () => renderUsageCards(usage, retrieved.length),
  };

  elements.debugContent.append((views[state.activeTab] || views.documents)());
}

function renderDocumentCard(document, options = {}) {
  const card = createEl("article", `document-card${options.compact ? " compact" : ""}`);
  const icon = createEl("div", "document-icon", "DOC");
  const content = createEl("div", "document-content");
  const title = createEl("strong", "", document.title || document.filename);
  const meta = createEl(
    "span",
    "document-meta",
    `${document.inserted_count}/${document.chunk_count} chunks - ${dateLabel(document.ingested_at)}`,
  );

  const status = createEl("div", "document-status-row");
  status.append(
    createEl("span", "status-chip success", "Markdown generated"),
    createEl("span", "status-chip success", "Indexed"),
    createEl("span", "status-chip neutral", document.chunking_strategy || "chunked"),
  );

  const links = createEl("div", "document-links");
  const original = createEl("a", "", "Original");
  original.href = document.doc_url;
  original.target = "_blank";
  original.rel = "noreferrer";
  const markdown = createEl("a", "", "Markdown");
  markdown.href = document.markdown_url;
  markdown.target = "_blank";
  markdown.rel = "noreferrer";
  links.append(original, markdown);

  content.append(title, meta, status, links);
  card.append(icon, content);
  return card;
}

function renderDocumentCards() {
  const documents = state.selectedAssistant?.documents || [];
  elements.documentsList.innerHTML = "";

  if (!documents.length) {
    elements.documentsList.append(createEl("p", "documents-empty", "Uploaded documents will appear here."));
    return;
  }

  for (const document of documents) {
    elements.documentsList.append(renderDocumentCard(document));
  }
}

function addProvenance(bubble, provenance) {
  if (!provenance?.length) {
    return;
  }

  const list = createEl("div", "provenance-list");
  list.append(createEl("div", "provenance-heading", "Sources used"));

  for (const item of provenance) {
    const card = createEl("article", "provenance-card");
    const top = createEl("div", "provenance-card-top");
    const link = createEl("a", "", item.title || item.filename || "source");
    link.href = item.doc_url;
    link.target = "_blank";
    link.rel = "noreferrer";

    const badge = createEl("span", `similarity-badge ${similarityClass(item.similarity)}`, compactNumber(item.similarity));
    top.append(link, badge);

    const meta = createEl("div", "provenance-meta", `Chunk ${item.chunk_number}`);
    card.append(top, meta);
    list.append(card);
  }

  bubble.append(list);
}

function renderEmptyState() {
  const empty = createEl("div", "empty-state");
  const glow = createEl("div", "empty-mark", "ER");
  const title = createEl("strong", "", "Start with a grounded question");
  const copy = createEl("p", "", "Connect documents to an assistant, then ask. EASY-RAG will answer with sources, similarities and token usage.");
  empty.append(glow, title, copy);
  elements.chatHistory.append(empty);
}

function appendMessageBubble(message, options = {}) {
  const roleName = options.label || message.role;
  const bubble = createEl("article", `message ${message.role}${options.pending ? " pending" : ""}`);
  const header = createEl("div", "message-header");
  const avatar = createEl("span", "avatar", message.role === "user" ? "👤" : "🤖");
  const role = createEl("span", "message-role", message.role === "user" ? "User" : "EASY-RAG");
  const time = createEl("time", "", timeLabel(message.created_at));
  header.append(avatar, role, time);

  const content = createEl("div", "message-content", message.content);
  if (options.pending) {
    content.classList.add("generation-steps");
    content.textContent = "";
    for (const step of ["Searching...", "Retrieving chunks...", "Generating answer..."]) {
      content.append(createEl("span", "", step));
    }
  }

  bubble.append(header, content);
  addProvenance(bubble, message.provenance);
  elements.chatHistory.append(bubble);
  return bubble;
}

function renderHistory() {
  const history = state.selectedAssistant?.history || [];
  elements.chatHistory.innerHTML = "";

  if (!history.length) {
    renderEmptyState();
    return;
  }

  for (const message of history) {
    appendMessageBubble(message);
  }

  elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
}

function renderPendingTurn(userInput) {
  renderHistory();
  appendMessageBubble({ role: "user", content: userInput });
  appendMessageBubble({ role: "assistant", content: "" }, { pending: true, label: "assistant" });
  elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
}

function updateChunkingVisibility() {
  const isSections = elements.chunkStrategy.value === "sections";
  document.querySelectorAll(".chars-only").forEach((item) => item.classList.toggle("is-hidden", isSections));
  document.querySelectorAll(".section-only").forEach((item) => item.classList.toggle("is-hidden", !isSections));
}

function applyAssistantValues(assistant) {
  elements.assistantName.value = assistant?.name || "";
  elements.systemPrompt.value = assistant?.system_prompt || DEFAULT_SYSTEM_PROMPT;
  elements.promptTemplate.value = assistant?.prompt_template || DEFAULT_TEMPLATE;
  elements.retrievalTopK.value = assistant?.retrieval_top_k || DEFAULTS.retrieval_top_k;
  elements.retrievalThreshold.value = assistant?.retrieval_threshold ?? DEFAULTS.retrieval_threshold;
  elements.chunkStrategy.value = assistant?.chunk_strategy || DEFAULTS.chunk_strategy;
  elements.chunkSize.value = assistant?.chunk_size || DEFAULTS.chunk_size;
  elements.chunkOverlap.value = assistant?.chunk_overlap ?? DEFAULTS.chunk_overlap;
  elements.sectionLevel.value = assistant?.section_level || DEFAULTS.section_level;
  updateChunkingVisibility();
}

function renderAssistantDetails() {
  const assistant = state.selectedAssistant;

  if (!assistant) {
    applyAssistantValues(null);
    elements.contextStatus.textContent = "No documents uploaded.";
    renderDocumentCards();
    renderHistory();
    renderDebug();
    return;
  }

  applyAssistantValues(assistant);
  const count = assistant.document_count || assistant.documents?.length || 0;
  const chunks = assistant.chunk_count || 0;
  elements.contextStatus.textContent = count ? `${count} docs / ${chunks} chunks` : "No documents uploaded.";
  renderDocumentCards();
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
  for (const control of form.querySelectorAll("button, input, select, textarea")) {
    control.disabled = busy;
  }
}

function renderSelectedFiles() {
  const files = [...elements.contextFile.files];
  elements.selectedFiles.innerHTML = "";

  if (!files.length) {
    return;
  }

  for (const file of files) {
    const item = createEl("div", "selected-file");
    item.append(createEl("strong", "", file.name), createEl("span", "", fileSizeLabel(file.size)));
    elements.selectedFiles.append(item);
  }
}

function setPanelVisibility(panel, visible) {
  const isSetup = panel === "setup";
  const button = isSetup ? elements.toggleSetup : elements.toggleDebug;
  const className = isSetup ? "setup-collapsed" : "debug-collapsed";
  state[isSetup ? "setupVisible" : "debugVisible"] = visible;
  elements.appShell.classList.toggle(className, !visible);
  button.setAttribute("aria-expanded", String(visible));
  button.textContent = visible ? (isSetup ? "Settings" : "RAG internals") : (isSetup ? "Show settings" : "Show internals");
}

elements.assistantForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(elements.assistantForm, true);
  elements.appStatus.textContent = "Saving assistant...";
  try {
    const isUpdate = Boolean(state.selectedAssistant?.id);
    const assistant = await api(isUpdate ? `/api/assistants/${state.selectedAssistant.id}` : "/api/assistants", {
      method: isUpdate ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(assistantPayload()),
    });
    await loadAssistants(assistant.id);
    showToast("Assistant saved.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(elements.assistantForm, false);
    renderStatusMetrics();
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

elements.chunkStrategy.addEventListener("change", updateChunkingVisibility);
elements.contextFile.addEventListener("change", renderSelectedFiles);

["dragenter", "dragover"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("drag-over");
  });
});

elements.dropZone.addEventListener("drop", (event) => {
  if (event.dataTransfer?.files?.length) {
    elements.contextFile.files = event.dataTransfer.files;
    renderSelectedFiles();
  }
});

elements.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedAssistant) {
    showToast("Create or select an assistant first.");
    return;
  }

  const files = [...elements.contextFile.files];
  if (!files.length) {
    showToast("Choose at least one document first.");
    return;
  }

  setBusy(elements.uploadForm, true);
  elements.uploadProgress.textContent = "Uploading... Converting to markdown... Indexing chunks...";
  elements.appStatus.textContent = "Indexing documents...";
  try {
    const body = new FormData();
    for (const file of files) {
      body.append("files", file);
    }
    const result = await api(`/api/assistants/${state.selectedAssistant.id}/documents`, {
      method: "POST",
      body,
    });
    state.selectedAssistant = result.assistant;
    elements.contextFile.value = "";
    renderSelectedFiles();
    await loadAssistants(state.selectedAssistant.id);
    showToast("Documents ingested.");
  } catch (error) {
    showToast(error.message);
  } finally {
    elements.uploadProgress.textContent = "";
    setBusy(elements.uploadForm, false);
    renderStatusMetrics();
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
  elements.appStatus.textContent = "Retrieving context...";
  renderPendingTurn(userInput);
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
    renderHistory();
    showToast(error.message);
  } finally {
    setBusy(elements.chatForm, false);
    elements.userInput.focus();
    renderStatusMetrics();
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

elements.toggleSetup.addEventListener("click", () => setPanelVisibility("setup", !state.setupVisible));
elements.toggleDebug.addEventListener("click", () => setPanelVisibility("debug", !state.debugVisible));

for (const tab of elements.tabs) {
  tab.addEventListener("click", () => {
    state.activeTab = tab.dataset.tab;
    for (const item of elements.tabs) {
      item.classList.toggle("active", item === tab);
    }
    renderDebug();
  });
}

applyAssistantValues(null);
renderSelectedFiles();
loadAssistants().catch((error) => showToast(error.message));
