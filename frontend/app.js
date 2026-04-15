/* ─────────────────────────────────────────────────────────────────
   Amenify AI Chat — app.js
   ───────────────────────────────────────────────────────────────── */

const API_BASE = window.location.origin;   // same origin as FastAPI

// ── State ────────────────────────────────────────────────────────
let sessionId = null;   // set after first API call
let isLoading = false;

// ── DOM references ───────────────────────────────────────────────
const messagesEl   = document.getElementById('messages');
const inputEl      = document.getElementById('user-input');
const sendBtn      = document.getElementById('send-btn');
const typingEl     = document.getElementById('typing-indicator');
const welcomeCard  = document.getElementById('welcome-card');
const btnNewChat   = document.getElementById('btn-new-chat');
const btnClear     = document.getElementById('btn-clear');
const suggChips    = document.querySelectorAll('.suggestion-chip');

// ── Helpers ──────────────────────────────────────────────────────
function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function scrollBottom() {
  messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
}

// ── Render a message bubble ──────────────────────────────────────
function appendMessage(role, text, sources = []) {
  // Hide welcome card on first real message
  if (welcomeCard) welcomeCard.style.display = 'none';

  const isUser  = role === 'user';
  const now     = new Date();

  const isUnknown = !isUser && text.toLowerCase().includes("i don't know");

  const row = document.createElement('div');
  row.className = `msg-row ${isUser ? 'user' : 'bot'}`;

  // Avatar
  const avatar = document.createElement('div');
  avatar.className = `msg-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`;
  avatar.textContent = isUser ? 'You' : 'A';

  // Bubble
  const bubble = document.createElement('div');
  bubble.className = `msg-bubble${isUnknown ? ' unknown' : ''}`;

  // Convert newlines to <br>
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');

  // Source chips (bot only)
  if (!isUser && sources.length > 0 && !isUnknown) {
    const chips = document.createElement('div');
    chips.className = 'source-chips';
    sources.forEach(src => {
      const chip = document.createElement('span');
      chip.className = 'source-chip';
      chip.textContent = new URL(src).hostname;
      chips.appendChild(chip);
    });
    bubble.appendChild(chips);
  }

  // Timestamp
  const timeEl = document.createElement('p');
  timeEl.className = 'msg-time';
  timeEl.textContent = formatTime(now);

  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'column';
  wrapper.appendChild(bubble);
  wrapper.appendChild(timeEl);

  row.appendChild(avatar);
  row.appendChild(wrapper);
  messagesEl.appendChild(row);
  scrollBottom();
}

// ── Show / hide typing indicator ─────────────────────────────────
function setTyping(show) {
  typingEl.classList.toggle('hidden', !show);
  if (show) scrollBottom();
}

// ── Auto-resize textarea ─────────────────────────────────────────
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  sendBtn.disabled = inputEl.value.trim() === '' || isLoading;
});

// ── Send message ─────────────────────────────────────────────────
async function sendMessage(text) {
  text = text.trim();
  if (!text || isLoading) return;

  isLoading = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  inputEl.style.height = 'auto';

  appendMessage('user', text);
  setTyping(true);

  try {
    const body = { message: text };
    if (sessionId) body.session_id = sessionId;

    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    sessionId = data.session_id;

    setTyping(false);
    appendMessage('bot', data.reply, data.sources || []);
  } catch (err) {
    setTyping(false);
    appendMessage('bot', `⚠️ Sorry, something went wrong: ${err.message}`);
  } finally {
    isLoading = false;
    sendBtn.disabled = inputEl.value.trim() === '';
  }
}

// ── Event listeners ──────────────────────────────────────────────
sendBtn.addEventListener('click', () => sendMessage(inputEl.value));

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(inputEl.value);
  }
});

// Suggestion chips
suggChips.forEach(chip => {
  chip.addEventListener('click', () => {
    sendMessage(chip.dataset.q);
  });
});

// New chat
btnNewChat.addEventListener('click', async () => {
  if (sessionId) {
    try {
      await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' });
    } catch (_) {}
    sessionId = null;
  }
  // clear messages, restore welcome card
  messagesEl.innerHTML = '';
  const card = document.createElement('div');
  card.className = 'welcome-card';
  card.id = 'welcome-card';
  card.innerHTML = `
    <div class="welcome-icon">🏡</div>
    <h2>Hi! I'm Amenify's AI assistant.</h2>
    <p>Ask me anything about our home services — cleaning, handyman, dog walking, grocery delivery, and more.</p>
    <p class="welcome-hint">← Use the sidebar suggestions or type below to get started!</p>
  `;
  messagesEl.appendChild(card);
  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;
});

// Clear (same as new chat for simplicity)
btnClear.addEventListener('click', () => btnNewChat.click());
