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

    // In-memory history: { sessionId: [{role, text}] }
    const chatHistory = {};

    // ── Init ─────────────────────────────────────────────────
    const firstItem = sessionsList.querySelector(".session-item");
    if (firstItem) {
        selectSession(firstItem.dataset.sessionId);
        firstItem.classList.add("active");
    }
    showEmptyState();

    // ── Auto-resize textarea ─────────────────────────────────
    userInput.addEventListener("input", () => {
        userInput.style.height = "auto";
        userInput.style.height = Math.min(userInput.scrollHeight, 160) + "px";
        const len = userInput.value.length;
        charCount.textContent = `${len} / 4000`;
        sendBtn.disabled = len === 0 || isStreaming;
    });

    // ── Enter to send ────────────────────────────────────────
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

    // ── New Chat ─────────────────────────────────────────────
    newChatBtn.addEventListener("click", async () => {
        try {
            newChatBtn.disabled = true;
            const res  = await fetch("/new_chat", { method: "POST" });
            const data = await res.json();
            chatHistory[data.session_id] = [];
            addSessionToSidebar(data.session_id);
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

    // ── Session click ─────────────────────────────────────────
    sessionsList.addEventListener("click", (e) => {
        const item = e.target.closest(".session-item");
        if (!item) return;
        selectSession(item.dataset.sessionId);
        renderHistory(item.dataset.sessionId);
        closeSidebar();
    });

    // ── Submit / Stream ───────────────────────────────────────
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message || isStreaming) return;
        if (!currentSession) { showToast("Please start a new conversation first"); return; }

        hideEmptyState();
        pushHistory(currentSession, "user", message);
        appendUserMessage(message);

        userInput.value = "";
        userInput.style.height = "auto";
        charCount.textContent = "0 / 4000";
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

        eventSource.onmessage = (event) => {
            // Server JSON-encodes each chunk → parse it back to recover \n etc.
            let chunk = event.data;
            try { chunk = JSON.parse(chunk); } catch (_) { /* use raw */ }
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
                pushHistory(sessionAtStart, "bot", fullText);
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

    // ════════════════════════════════════════════════════════
    //  MARKDOWN RENDERER
    //  Strategy: extract code blocks first → protect them →
    //  process prose → reinsert code blocks.
    // ════════════════════════════════════════════════════════

    function renderMarkdown(raw) {
        // ── Step 1: pull out all fenced code blocks into a safe store ──
        const codeStore = [];
        const withPlaceholders = raw.replace(
            /```([\w]*)\n?([\s\S]*?)```/g,
            (_, lang, code) => {
                const idx = codeStore.length;
                codeStore.push({ lang: lang.trim(), code });
                return `\x00CODE${idx}\x00`;          // null-byte placeholder
            }
        );

        // ── Step 2: process prose (never touches placeholders) ──
        let html = processProse(withPlaceholders);

        // ── Step 3: restore code blocks ──
        html = html.replace(/\x00CODE(\d+)\x00/g, (_, idx) => {
            const { lang, code } = codeStore[Number(idx)];
            return buildCodeBlock(lang, code);
        });

        return html;
    }

    function processProse(text) {
        let t = text;

        // Escape HTML entities (but not inside placeholders)
        t = t.replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;");

        // Headings (process before inline rules)
        t = t.replace(/^### (.+)$/gm,  "<h4>$1</h4>");
        t = t.replace(/^## (.+)$/gm,   "<h3>$1</h3>");
        t = t.replace(/^# (.+)$/gm,    "<h2>$1</h2>");

        // Horizontal rule
        t = t.replace(/^---$/gm, "<hr>");

        // Ordered list
        t = t.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
        t = t.replace(/(<li>.*<\/li>\n?)+/g, m => `<ol>${m}</ol>`);

        // Unordered list
        t = t.replace(/^[*\-] (.+)$/gm, "<li>$1</li>");
        // Wrap consecutive <li> not already in <ol>
        t = t.replace(/(<li>(?!.*<\/ol>).*<\/li>\n?)+/g, m =>
            m.includes("<ol>") ? m : `<ul>${m}</ul>`
        );

        // Bold + italic ***text***
        t = t.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
        // Bold **text**
        t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        // Italic *text*
        t = t.replace(/\*([^*\n]+?)\*/g, "<em>$1</em>");

        // Inline code `code`
        t = t.replace(/`([^`\n]+)`/g,
            (_, c) => `<code>${c.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">")}</code>`
        );

        // Newlines → <br>  (LAST — after all block-level rules)
        t = t.replace(/\n/g, "<br>");

        return t;
    }

    function buildCodeBlock(lang, code) {
        // code still has raw newlines — escapeHtml preserves them inside <pre>
        const escaped  = code
            .replace(/&/g,  "&amp;")
            .replace(/</g,  "&lt;")
            .replace(/>/g,  "&gt;")
            .replace(/"/g,  "&quot;");
        const langLabel = lang
            ? `<span class="code-lang">${lang.toUpperCase()}</span>`
            : `<span class="code-lang">CODE</span>`;
        const encoded = encodeURIComponent(code);

        return `<div class="code-block-wrapper">
                    <div class="code-block-header">
                        ${langLabel}
                        <button class="copy-btn" data-code="${encoded}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                            Copy
                        </button>
                    </div>
                    <pre><code>${escaped}</code></pre>
                </div>`;
    }

    // ── Copy buttons ─────────────────────────────────────────
    function attachCopyButtons(container) {
        container.querySelectorAll(".copy-btn").forEach(btn => {
            const fresh = btn.cloneNode(true);
            btn.replaceWith(fresh);
            fresh.addEventListener("click", () => {
                const code = decodeURIComponent(fresh.dataset.code);
                navigator.clipboard.writeText(code).then(() => {
                    fresh.classList.add("copied");
                    fresh.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/></svg> Copied!`;
                    setTimeout(() => {
                        fresh.classList.remove("copied");
                        fresh.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg> Copy`;
                    }, 2000);
                }).catch(() => showToast("Copy failed"));
            });
        });
    }

    // ════════════════════════════════════════════════════════
    //  HISTORY
    // ════════════════════════════════════════════════════════

    function pushHistory(sid, role, text) {
        if (!chatHistory[sid]) chatHistory[sid] = [];
        chatHistory[sid].push({ role, text });
    }

    function renderHistory(sid) {
        chatBox.innerHTML = "";
        const history = chatHistory[sid] || [];
        if (!history.length) { showEmptyState(); return; }
        hideEmptyState();
        history.forEach(({ role, text }) => {
            if (role === "user") {
                appendUserMessage(text);
            } else {
                const row = createBotMessageRow();
                const bubble = row.querySelector(".message-bubble");
                bubble.innerHTML = renderMarkdown(text);
                attachCopyButtons(bubble);
                chatBox.appendChild(row);
            }
        });
        scrollToBottom();
    }

    // ════════════════════════════════════════════════════════
    //  UI HELPERS
    // ════════════════════════════════════════════════════════

    function selectSession(id) {
        currentSession = id;
        sessionLabel.textContent = id ? id.slice(0, 18) + "…" : "No active session";
        sessionIndicator.classList.toggle("active", !!id);
        document.querySelectorAll(".session-item").forEach(el =>
            el.classList.toggle("active", el.dataset.sessionId === id)
        );
    }

    function addSessionToSidebar(id) {
        const item = document.createElement("div");
        item.className = "session-item";
        item.dataset.sessionId = id;
        item.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span class="session-label">${id.slice(0, 8)}…</span>`;
        sessionsList.prepend(item);
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
            <div class="message-bubble" style="padding:10px 16px">
                <div class="typing-indicator"><span></span><span></span><span></span></div>
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
