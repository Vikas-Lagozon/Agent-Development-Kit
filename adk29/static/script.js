/* ============================================================
   JARVIS — script.js
   ============================================================ */

(function () {
    "use strict";

    // ── DOM refs ────────────────────────────────────────────
    const chatBox          = document.getElementById("chat-box");
    const chatForm         = document.getElementById("chat-form");
    const userInput        = document.getElementById("user-input");
    const sendBtn          = document.getElementById("send-btn");
    const newChatBtn       = document.getElementById("new-chat-btn");
    const sessionsList     = document.getElementById("sessions-list");
    const sessionLabel     = document.getElementById("current-session-label");
    const sessionIndicator = document.getElementById("session-indicator");
    const emptyState       = document.getElementById("empty-state");
    const charCount        = document.getElementById("char-count");
    const mobileMenuBtn    = document.getElementById("mobile-menu-btn");
    const sidebar          = document.getElementById("sidebar");
    const sidebarOverlay   = document.getElementById("sidebar-overlay");

    let currentSession = null;
    let isStreaming    = false;

    // { sessionId: { name, created_at, messages: [{role,text}], _historyFetched: bool } }
    const sessionStore = {};

    // ── Bootstrap sessions from server-rendered HTML ─────────
    document.querySelectorAll(".session-item").forEach(item => {
        const id      = item.dataset.sessionId;
        const name    = item.dataset.name || id.slice(0, 8) + "…";
        const created = item.dataset.createdAt || "";
        sessionStore[id] = { name, created_at: created, messages: [], _historyFetched: false };
    });

    rebuildSidebar();

    // Auto-select the first session and load its history
    const firstItem = sessionsList.querySelector(".session-item");
    if (firstItem) {
        selectSession(firstItem.dataset.sessionId);
        renderHistory(firstItem.dataset.sessionId);   // async — will show content once fetched
    } else {
        showEmptyState();
    }

    // ── Auto-resize textarea ─────────────────────────────────
    userInput.addEventListener("input", () => {
        userInput.style.height = "auto";
        userInput.style.height = Math.min(userInput.scrollHeight, 160) + "px";
        const len = userInput.value.length;
        charCount.textContent = `${len} / 25000`;
        sendBtn.disabled = len === 0 || isStreaming;
    });

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // ── Suggestion chips ─────────────────────────────────────
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            userInput.value = chip.dataset.text;
            userInput.dispatchEvent(new Event("input"));
            userInput.focus();
        });
    });

    // ── Mobile sidebar ────────────────────────────────────────
    mobileMenuBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        sidebarOverlay.classList.toggle("visible");
    });
    sidebarOverlay.addEventListener("click", closeSidebar);
    function closeSidebar() {
        sidebar.classList.remove("open");
        sidebarOverlay.classList.remove("visible");
    }

    // ══════════════════════════════════════════════════════════
    //  NEW CHAT
    // ══════════════════════════════════════════════════════════
    newChatBtn.addEventListener("click", async () => {
        try {
            newChatBtn.disabled = true;
            const res  = await fetch("/new_chat", { method: "POST" });
            const data = await res.json();
            sessionStore[data.session_id] = {
                name:            data.name,
                created_at:      data.created_at,
                messages:        [],
                _historyFetched: true,   // brand-new session — nothing to fetch
            };
            rebuildSidebar();
            selectSession(data.session_id);
            renderHistory(data.session_id);
            showToast("New conversation started");
            closeSidebar();
        } catch (err) {
            showToast("Failed to create session");
            console.error(err);
        } finally {
            newChatBtn.disabled = false;
        }
    });

    // ══════════════════════════════════════════════════════════
    //  SIDEBAR CLICK DELEGATION
    //  handles: select · rename · delete
    // ══════════════════════════════════════════════════════════
    sessionsList.addEventListener("click", (e) => {
        const renameBtn = e.target.closest(".btn-rename");
        const deleteBtn = e.target.closest(".btn-delete");
        const item      = e.target.closest(".session-item");
        if (!item) return;

        const id = item.dataset.sessionId;

        if (renameBtn) { e.stopPropagation(); startRename(id, item); return; }
        if (deleteBtn) { e.stopPropagation(); confirmDelete(id);      return; }

        selectSession(id);
        renderHistory(id);
        closeSidebar();
    });

    // ── Rename ────────────────────────────────────────────────
    function startRename(id, itemEl) {
        const labelEl = itemEl.querySelector(".session-label");
        const current = sessionStore[id]?.name || "";

        const input = document.createElement("input");
        input.className   = "rename-input";
        input.value       = current;
        input.maxLength   = 40;
        labelEl.replaceWith(input);
        input.focus();
        input.select();

        const commit = async () => {
            const newName = input.value.trim() || current;
            try {
                await fetch(`/session/${id}/rename`, {
                    method:  "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body:    JSON.stringify({ name: newName }),
                });
                if (sessionStore[id]) sessionStore[id].name = newName;
                rebuildSidebar();
                if (currentSession === id) {
                    sessionLabel.textContent = truncate(newName, 20);
                }
                showToast("Session renamed");
            } catch {
                showToast("Rename failed");
                rebuildSidebar();
            }
        };

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter")  { e.preventDefault(); commit(); }
            if (e.key === "Escape") { rebuildSidebar(); }
        });
        input.addEventListener("blur", commit);
    }

    // ── Delete ────────────────────────────────────────────────
    function confirmDelete(id) {
        showConfirm(
            "Delete this conversation?",
            "This cannot be undone.",
            async () => {
                try {
                    await fetch(`/session/${id}`, { method: "DELETE" });
                    delete sessionStore[id];
                    rebuildSidebar();
                    if (currentSession === id) {
                        // Switch to first remaining session or clear
                        const remaining = Object.keys(sessionStore);
                        if (remaining.length) {
                            selectSession(remaining[0]);
                            renderHistory(remaining[0]);
                        } else {
                            currentSession = null;
                            sessionLabel.textContent = "No active session";
                            sessionIndicator.classList.remove("active");
                            chatBox.innerHTML = "";
                            showEmptyState();
                        }
                    }
                    showToast("Conversation deleted");
                } catch {
                    showToast("Delete failed");
                }
            }
        );
    }

    // ══════════════════════════════════════════════════════════
    //  SUBMIT / STREAM
    // ══════════════════════════════════════════════════════════
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message || isStreaming) return;
        if (!currentSession) { showToast("Please start a new conversation first"); return; }

        hideEmptyState();
        pushMessage(currentSession, "user", message);
        appendUserMessage(message);

        // Auto-rename session after first user message
        if (sessionStore[currentSession]?.name === "New Chat") {
            const autoName = message.slice(0, 30) + (message.length > 30 ? "…" : "");
            sessionStore[currentSession].name = autoName;
            rebuildSidebar();
            sessionLabel.textContent = truncate(autoName, 20);
        }

        userInput.value = "";
        userInput.style.height = "auto";
        charCount.textContent = "0 / 25000";
        sendBtn.disabled = true;
        isStreaming = true;

        const typingRow = createTypingIndicator();
        chatBox.appendChild(typingRow);
        scrollToBottom();

        const params = new URLSearchParams({ user_input: message, session_id: currentSession });
        const eventSource = new EventSource(`/chat/stream?${params.toString()}`);

        let botBubble = null;
        let fullText  = "";
        const sessionAtStart = currentSession;

        eventSource.onopen = () => {
            typingRow.remove();
            const row = createBotMessageRow();
            chatBox.appendChild(row);
            botBubble = row.querySelector(".message-bubble");
            scrollToBottom();
        };

        eventSource.onmessage = (ev) => {
            let chunk = ev.data;
            try { chunk = JSON.parse(chunk); } catch (_) {}
            fullText += chunk;
            if (botBubble) {
                botBubble.innerHTML = renderMarkdown(fullText);
                attachCopyButtons(botBubble);
                scrollToBottom();
            }
        };

        const onDone = () => {
            eventSource.close();
            typingRow.remove();
            if (botBubble && fullText) {
                botBubble.innerHTML = renderMarkdown(fullText);
                attachCopyButtons(botBubble);
                pushMessage(sessionAtStart, "bot", fullText);
            } else if (!botBubble) {
                const errRow = document.createElement("div");
                errRow.className = "message-row bot";
                errRow.innerHTML = `${botAvatarHTML()}
                    <div class="message-bubble error-bubble">⚠ Something went wrong. Please try again.</div>`;
                chatBox.appendChild(errRow);
                scrollToBottom();
            }
            isStreaming = false;
            sendBtn.disabled = userInput.value.trim() === "";
        };

        eventSource.onerror = onDone;
        eventSource.addEventListener("close", onDone);
    });

    // ══════════════════════════════════════════════════════════
    //  SIDEBAR BUILDER  (with date grouping)
    // ══════════════════════════════════════════════════════════
    function rebuildSidebar() {
        sessionsList.innerHTML = "";

        // Group sessions by date label
        const groups = {};   // { "Today": [...], "Yesterday": [...], "Older": [...] }
        const now    = new Date();

        Object.entries(sessionStore).forEach(([id, meta]) => {
            const label = dateGroupLabel(meta.created_at, now);
            if (!groups[label]) groups[label] = [];
            groups[label].push({ id, ...meta });
        });

        // Sort each group newest-first
        const groupOrder = ["Today", "Yesterday", "This Week", "Older"];
        groupOrder.forEach(groupLabel => {
            const items = groups[groupLabel];
            if (!items || !items.length) return;

            items.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));

            // Date group header
            const header = document.createElement("div");
            header.className = "date-group-header";
            header.textContent = groupLabel;
            sessionsList.appendChild(header);

            items.forEach(({ id, name }) => {
                sessionsList.appendChild(buildSessionItem(id, name));
            });
        });

        // Re-highlight active
        document.querySelectorAll(".session-item").forEach(el =>
            el.classList.toggle("active", el.dataset.sessionId === currentSession)
        );
    }

    function buildSessionItem(id, name) {
        const item = document.createElement("div");
        item.className        = "session-item";
        item.dataset.sessionId = id;
        item.innerHTML = `
            <svg class="session-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span class="session-label">${escapeHtml(name)}</span>
            <div class="session-actions">
                <button class="btn-rename session-action-btn" title="Rename">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                </button>
                <button class="btn-delete session-action-btn" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6l-1 14H6L5 6"/>
                        <path d="M10 11v6M14 11v6"/>
                        <path d="M9 6V4h6v2"/>
                    </svg>
                </button>
            </div>`;
        return item;
    }

    function dateGroupLabel(isoString, now) {
        if (!isoString) return "Older";
        const d    = new Date(isoString);
        if (isNaN(d.getTime())) return "Older";
        const diff = Math.floor((now - d) / 86400000);
        if (diff === 0) return "Today";
        if (diff === 1) return "Yesterday";
        if (diff <= 6) return "This Week";
        return "Older";
    }

    // ══════════════════════════════════════════════════════════
    //  HISTORY
    //  renderHistory is async: fetches from server on cache miss
    // ══════════════════════════════════════════════════════════
    function pushMessage(sid, role, text) {
        if (!sessionStore[sid]) sessionStore[sid] = { messages: [], _historyFetched: true };
        if (!sessionStore[sid].messages) sessionStore[sid].messages = [];
        sessionStore[sid].messages.push({ role, text });
    }

    async function renderHistory(sid) {
        chatBox.innerHTML = "";

        const store = sessionStore[sid];
        if (!store) { showEmptyState(); return; }

        // ── Fetch from server if we haven't yet for this session ──
        if (!store._historyFetched) {
            store._historyFetched = true;  // mark before fetch to prevent duplicate calls
            try {
                const res  = await fetch(`/session/${sid}/history`);
                const data = await res.json();
                if (data.messages && data.messages.length) {
                    store.messages = data.messages;
                }
            } catch (err) {
                console.error("Failed to load chat history:", err);
            }
        }

        const messages = store.messages || [];
        if (!messages.length) { showEmptyState(); return; }

        hideEmptyState();
        messages.forEach(({ role, text }) => {
            if (role === "user") {
                appendUserMessage(text);
            } else {
                const row = createBotMessageRow();
                row.querySelector(".message-bubble").innerHTML = renderMarkdown(text);
                attachCopyButtons(row.querySelector(".message-bubble"));
                chatBox.appendChild(row);
            }
        });
        scrollToBottom();
    }

    // ══════════════════════════════════════════════════════════
    //  MARKDOWN RENDERER
    // ══════════════════════════════════════════════════════════
    function renderMarkdown(raw) {
        const codeStore = [];
        const withPlaceholders = raw.replace(
            /```([\w]*)\n?([\s\S]*?)```/g,
            (_, lang, code) => {
                codeStore.push({ lang: lang.trim(), code });
                return `\x00CODE${codeStore.length - 1}\x00`;
            }
        );

        let html = processProse(withPlaceholders);

        html = html.replace(/\x00CODE(\d+)\x00/g, (_, idx) => {
            const { lang, code } = codeStore[Number(idx)];
            return buildCodeBlock(lang, code);
        });

        return html;
    }

    function processProse(text) {
        let t = escapeHtml(text);
        t = t.replace(/^### (.+)$/gm, "<h4>$1</h4>");
        t = t.replace(/^## (.+)$/gm,  "<h3>$1</h3>");
        t = t.replace(/^# (.+)$/gm,   "<h2>$1</h2>");
        t = t.replace(/^---$/gm, "<hr>");
        t = t.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
        t = t.replace(/(<li>.*<\/li>\n?)+/g, m => `<ol>${m}</ol>`);
        t = t.replace(/^[*\-] (.+)$/gm, "<li>$1</li>");
        t = t.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
        t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        t = t.replace(/\*([^*\n]+?)\*/g, "<em>$1</em>");
        t = t.replace(/`([^`\n]+)`/g,
            (_, c) => `<code>${c.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">")}</code>`
        );
        t = t.replace(/\n/g, "<br>");
        return t;
    }

    function buildCodeBlock(lang, code) {
        const escaped   = escapeHtml(code);
        const langLabel = `<span class="code-lang">${lang ? lang.toUpperCase() : "CODE"}</span>`;
        const encoded   = encodeURIComponent(code);
        return `<div class="code-block-wrapper">
                    <div class="code-block-header">
                        ${langLabel}
                        <button class="copy-btn" data-code="${encoded}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>Copy
                        </button>
                    </div>
                    <pre><code>${escaped}</code></pre>
                </div>`;
    }

    function attachCopyButtons(container) {
        container.querySelectorAll(".copy-btn").forEach(btn => {
            const fresh = btn.cloneNode(true);
            btn.replaceWith(fresh);
            fresh.addEventListener("click", () => {
                const code = decodeURIComponent(fresh.dataset.code);
                navigator.clipboard.writeText(code).then(() => {
                    fresh.classList.add("copied");
                    fresh.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/></svg>Copied!`;
                    setTimeout(() => {
                        fresh.classList.remove("copied");
                        fresh.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>Copy`;
                    }, 2000);
                }).catch(() => showToast("Copy failed"));
            });
        });
    }

    // ══════════════════════════════════════════════════════════
    //  CONFIRM DIALOG
    // ══════════════════════════════════════════════════════════
    function showConfirm(title, subtitle, onConfirm) {
        const overlay = document.createElement("div");
        overlay.className = "confirm-overlay";
        overlay.innerHTML = `
            <div class="confirm-box">
                <div class="confirm-title">${title}</div>
                <div class="confirm-subtitle">${subtitle}</div>
                <div class="confirm-actions">
                    <button class="confirm-cancel">Cancel</button>
                    <button class="confirm-ok">Delete</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector(".confirm-cancel").addEventListener("click", () => overlay.remove());
        overlay.querySelector(".confirm-ok").addEventListener("click", () => {
            overlay.remove();
            onConfirm();
        });
    }

    // ══════════════════════════════════════════════════════════
    //  UI HELPERS
    // ══════════════════════════════════════════════════════════
    function selectSession(id) {
        currentSession = id;
        const name = sessionStore[id]?.name || id.slice(0, 18) + "…";
        sessionLabel.textContent = truncate(name, 20);
        sessionIndicator.classList.toggle("active", !!id);
        document.querySelectorAll(".session-item").forEach(el =>
            el.classList.toggle("active", el.dataset.sessionId === id)
        );
    }

    function appendUserMessage(text) {
        const row = document.createElement("div");
        row.className = "message-row user";
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        bubble.textContent = text;
        row.appendChild(bubble);
        chatBox.appendChild(row);
        scrollToBottom();
    }

    function botAvatarHTML() {
        return `<div class="bot-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke-linejoin="round"/>
            </svg>
        </div>`;
    }

    function createBotMessageRow() {
        const row = document.createElement("div");
        row.className = "message-row bot";
        row.innerHTML = `${botAvatarHTML()}<div class="message-bubble"></div>`;
        return row;
    }

    function createTypingIndicator() {
        const row = document.createElement("div");
        row.className = "message-row bot";
        row.innerHTML = `${botAvatarHTML()}
            <div class="message-bubble waiting-bubble">
                <div class="waiting-spinner">
                    <svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="20" cy="20" r="16" fill="none" stroke-width="3"
                                class="spinner-track"/>
                        <circle cx="20" cy="20" r="16" fill="none" stroke-width="3"
                                class="spinner-arc"/>
                    </svg>
                </div>
                <span class="waiting-label">Thinking…</span>
            </div>`;
        return row;
    }

    function hideEmptyState() {
        emptyState.classList.add("hidden");
        chatBox.style.display = "flex";
    }
    function showEmptyState() {
        emptyState.classList.remove("hidden");
        chatBox.style.display = "none";
    }
    function scrollToBottom() {
        requestAnimationFrame(() => { chatBox.scrollTop = chatBox.scrollHeight; });
    }
    function truncate(str, n) {
        return str.length > n ? str.slice(0, n) + "…" : str;
    }
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g,  "&amp;")
            .replace(/</g,  "&lt;")
            .replace(/>/g,  "&gt;")
            .replace(/"/g,  "&quot;");
    }
    function showToast(msg) {
        const old = document.querySelector(".toast");
        if (old) old.remove();
        const t = document.createElement("div");
        t.className = "toast";
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3000);
    }

})();