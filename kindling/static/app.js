const BASE = "/kindling/api";

// ── State ────────────────────────────────────────────────────────────────────
let pendingImage = null; // { b64, type, name }

// ── Tab switching ────────────────────────────────────────────────────────────

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".bottom-nav button").forEach((b) => b.classList.remove("active"));
  const tab = document.getElementById("tab-" + name);
  if (tab) tab.classList.add("active");
  const nav = document.getElementById("nav-" + name);
  if (nav) nav.classList.add("active");

  if (name === "track") loadTrack();
  if (name === "settings") loadSettings();
  if (name === "history") loadHistory();
  if (name === "motivate") {
    if (!document.getElementById("quote-text").textContent) shuffleQuote();
    if (!document.getElementById("therapy-text").textContent) shuffleTherapy();
  }
}

// ── Chat ─────────────────────────────────────────────────────────────────────

function addBubble(role, text, imgSrc) {
  const box = document.getElementById("chat-messages");
  const d = document.createElement("div");
  d.className = "bubble " + role;
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = role === "user" ? "You" : role === "error" ? "Error" : "Assistant";
  d.appendChild(name);
  if (imgSrc) {
    const img = document.createElement("img");
    img.className = "img-thumb";
    img.src = imgSrc;
    d.appendChild(img);
  }
  d.appendChild(document.createTextNode(text));
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
  return d;
}

function addTyping() {
  const box = document.getElementById("chat-messages");
  const d = document.createElement("div");
  d.className = "typing";
  d.id = "typing-indicator";
  d.textContent = "typing...";
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

async function sendMessage() {
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg && !pendingImage) return;
  input.value = "";

  // Show user bubble with image thumbnail if attached
  const displayText = pendingImage && msg ? "[Screenshot]\n" + msg : pendingImage ? "[Screenshot attached]" : msg;
  const thumbSrc = pendingImage ? "data:" + pendingImage.type + ";base64," + pendingImage.b64 : null;
  addBubble("user", displayText, thumbSrc);
  addTyping();
  document.getElementById("send-btn").disabled = true;

  const payload = { message: msg || "Please analyze this image" };
  if (pendingImage) {
    payload.image_b64 = pendingImage.b64;
    payload.image_type = pendingImage.type;
  }
  clearImage();

  try {
    const r = await fetch(BASE + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    removeTyping();
    const d = await r.json();
    if (!r.ok) {
      addBubble("error", d.detail || "Something went wrong");
    } else {
      addBubble("assistant", d.reply);
    }
  } catch (e) {
    removeTyping();
    addBubble("error", "Connection failed. Check your internet.");
  }
  document.getElementById("send-btn").disabled = false;
}

async function clearChat() {
  await fetch(BASE + "/chat/clear", { method: "POST" });
  document.getElementById("chat-messages").innerHTML = "";
  addBubble("assistant", "Chat cleared. What would you like help with?");
}

async function startNewChat() {
  await fetch(BASE + "/chat/new", { method: "POST" });
  document.getElementById("chat-messages").innerHTML = "";
  addBubble("assistant", "New chat started! Previous chat saved to history.\n\nWhat would you like help with?");
  switchTab("chat");
}

// Enter key sends
document.getElementById("chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

// ── Image attachment ─────────────────────────────────────────────────────────

function onImagePicked(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const b64 = reader.result.split(",")[1];
    pendingImage = { b64, type: file.type || "image/jpeg", name: file.name };
    document.getElementById("img-preview").style.display = "flex";
    document.getElementById("img-preview-name").textContent = file.name.length > 30 ? file.name.slice(0, 27) + "..." : file.name;
  };
  reader.readAsDataURL(file);
  input.value = "";
}

function clearImage() {
  pendingImage = null;
  document.getElementById("img-preview").style.display = "none";
  document.getElementById("img-preview-name").textContent = "";
}

// ── Chat history ─────────────────────────────────────────────────────────────

async function loadHistory() {
  const box = document.getElementById("history-list");
  box.innerHTML = "<p style='color:#999;text-align:center;padding:20px'>Loading...</p>";
  try {
    const r = await fetch(BASE + "/chat/history");
    const d = await r.json();
    box.innerHTML = "";
    if (!d.sessions.length) {
      box.innerHTML = "<p style='color:#999;text-align:center;padding:40px'>No saved chats yet. Start a conversation and tap + to begin a new one.</p>";
      return;
    }
    d.sessions.forEach((s) => {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML =
        '<div class="hi-text" onclick=\'resumeChat("' + s.id + '")\'>' +
        '<div class="hi-title">' + esc(s.title) + "</div>" +
        '<div class="hi-date">' + esc(s.date) + " — " + s.count + " messages</div>" +
        "</div>" +
        '<button class="hi-delete" onclick=\'deleteChat("' + s.id + '\")\'>' + "&#128465;</button>";
      box.appendChild(div);
    });
  } catch (e) {
    box.innerHTML = "<p style='color:#c62828;text-align:center'>Failed to load history</p>";
  }
}

async function resumeChat(chatId) {
  try {
    const r = await fetch(BASE + "/chat/history/" + chatId + "/resume", { method: "POST" });
    const d = await r.json();
    if (r.ok) {
      // Render the restored messages
      document.getElementById("chat-messages").innerHTML = "";
      d.messages.forEach((m) => {
        addBubble(m.role, typeof m.content === "string" ? m.content : m.content);
      });
      addBubble("assistant", "Chat resumed. Continue where you left off!");
      switchTab("chat");
    }
  } catch (e) {}
}

async function deleteChat(chatId) {
  await fetch(BASE + "/chat/history", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId }),
  });
  loadHistory();
}

// ── Icebreakers ──────────────────────────────────────────────────────────────

async function genOpener(kind) {
  const ctx = document.getElementById("ice-context").value.trim();
  const box = document.getElementById("ice-results");
  box.innerHTML = '<div class="ice-result">Generating ideas...</div>';

  try {
    const r = await fetch(BASE + "/icebreakers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, context: ctx }),
    });
    const d = await r.json();
    if (!r.ok) {
      box.innerHTML = '<div class="ice-result" style="color:#c62828">' + esc(d.detail || "Error") + "</div>";
    } else {
      box.innerHTML = '<div class="ice-result">' + esc(d.reply) + "</div>";
    }
  } catch (e) {
    box.innerHTML = '<div class="ice-result" style="color:#c62828">Connection failed</div>';
  }
}

// ── Track ────────────────────────────────────────────────────────────────────

async function loadTrack() {
  try {
    const r = await fetch(BASE + "/track");
    const d = await r.json();
    document.getElementById("wins-count").textContent = "Wins: " + d.wins;
    document.getElementById("fails-count").textContent = "Learning: " + d.fails;

    const box = document.getElementById("track-list");
    box.innerHTML = "";
    d.entries.forEach((e) => {
      const isWin = e.kind === "success";
      const div = document.createElement("div");
      div.className = "track-entry " + (isWin ? "win" : "miss");
      div.innerHTML =
        '<span class="text">' + (isWin ? "&#8226; Win" : "&#8226; Miss") + "  " + esc(e.date || "") + "  —  " + esc(e.note || "(no note)") + "</span>" +
        '<button onclick=\'editTrack(' + JSON.stringify(JSON.stringify(e)) + ")'>" + "&#9998;</button>" +
        '<button onclick=\'deleteTrack(' + JSON.stringify(JSON.stringify(e)) + ")'>" + "&#128465;</button>";
      box.appendChild(div);
    });
  } catch (e) {}
}

async function logTrack(kind) {
  const note = document.getElementById("track-note").value.trim();
  await fetch(BASE + "/track", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, note }),
  });
  document.getElementById("track-note").value = "";
  loadTrack();
}

function editTrack(entryJson) {
  const e = JSON.parse(entryJson);
  showModal("Edit entry", e.note || "", (newNote) => {
    fetch(BASE + "/track", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: e.kind, date: e.date, old_note: e.note || "", new_note: newNote }),
    }).then(() => loadTrack());
  }, true);
}

async function deleteTrack(entryJson) {
  const e = JSON.parse(entryJson);
  await fetch(BASE + "/track", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind: e.kind, date: e.date, note: e.note || "" }),
  });
  loadTrack();
}

// ── Motivate ─────────────────────────────────────────────────────────────────

async function shuffleQuote() {
  try {
    const r = await fetch(BASE + "/motivate/quote");
    const d = await r.json();
    document.getElementById("quote-text").textContent = d.quote;
  } catch (e) {}
}

async function shuffleTherapy() {
  try {
    const r = await fetch(BASE + "/motivate/therapy");
    const d = await r.json();
    document.getElementById("therapy-text").textContent = d.tip;
  } catch (e) {}
}

// ── Settings ─────────────────────────────────────────────────────────────────

let currentProvider = "gemini";
let settingsData = {};

async function loadSettings() {
  try {
    const r = await fetch(BASE + "/settings");
    settingsData = await r.json();
    currentProvider = settingsData.provider;

    // Provider buttons
    const box = document.getElementById("provider-btns");
    box.innerHTML = "";
    settingsData.providers.forEach((p) => {
      const btn = document.createElement("button");
      btn.textContent = settingsData.provider_labels[p];
      btn.className = p === currentProvider ? "active" : "";
      btn.onclick = () => setProvider(p);
      box.appendChild(btn);
    });

    document.getElementById("provider-hint").textContent = settingsData.provider_hints[currentProvider] || "";
    document.getElementById("api-key-input").placeholder = settingsData.provider_hints[currentProvider] || "API Key";

    // Profiles
    renderProfiles(settingsData.profiles, settingsData.active_profile);
  } catch (e) {}
}

async function setProvider(p) {
  await fetch(BASE + "/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: p }),
  });
  loadSettings();
}

async function saveAndConnect() {
  const key = document.getElementById("api-key-input").value.trim();
  if (!key) { showStatus("Enter an API key first."); return; }
  await fetch(BASE + "/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: key }),
  });
  showStatus("Testing connection...");
  try {
    const r = await fetch(BASE + "/settings/test", { method: "POST" });
    const d = await r.json();
    showStatus(r.ok ? "Connected (OK)" : "Failed: " + (d.detail || "Unknown error"));
  } catch (e) {
    showStatus("Connection failed");
  }
}

async function saveKey() {
  const key = document.getElementById("api-key-input").value.trim();
  await fetch(BASE + "/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: key }),
  });
  showStatus(key ? "Saved." : "Key cleared.");
}

function showStatus(msg) {
  const el = document.getElementById("settings-status");
  el.textContent = msg;
  setTimeout(() => { el.textContent = ""; }, 4000);
}

// ── Profiles ─────────────────────────────────────────────────────────────────

function renderProfiles(profiles, active) {
  const box = document.getElementById("profile-cards");
  box.innerHTML = "";
  const names = Object.keys(profiles);

  names.forEach((name) => {
    const bio = profiles[name];
    const isActive = name === active;
    const card = document.createElement("div");
    card.className = "profile-card" + (isActive ? " active" : "");

    let preview = bio ? (bio.length > 80 ? bio.slice(0, 80) + "..." : bio) : "No bio yet — tap edit to add one.";
    let actions = "";
    if (!isActive) actions += '<button onclick=\'switchProfile("' + esc(name) + "\")'>" + "&#9989;</button>";
    actions += '<button onclick=\'editProfile("' + esc(name) + "\")'>" + "&#9998;</button>";
    if (names.length > 1) actions += '<button onclick=\'deleteProfile("' + esc(name) + "\")'>" + "&#128465;</button>";

    card.innerHTML =
      '<div class="pname">' + (isActive ? "&#8226; " : "") + esc(name) + "</div>" +
      '<div class="pbio">' + esc(preview) + "</div>" +
      '<div class="pactions">' + actions + "</div>";
    box.appendChild(card);
  });
}

function showCreateProfile() {
  showModal("New Profile", "", async (name) => {
    if (!name.trim()) return;
    await fetch(BASE + "/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    loadSettings();
  });
}

async function switchProfile(name) {
  await fetch(BASE + "/profiles/switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  loadSettings();
}

function editProfile(name) {
  const bio = (settingsData.profiles && settingsData.profiles[name]) || "";
  showModal('Edit "' + name + '"', bio, async (newBio) => {
    await fetch(BASE + "/profiles", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, bio: newBio }),
    });
    loadSettings();
  }, true);
}

async function deleteProfile(name) {
  await fetch(BASE + "/profiles", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  loadSettings();
}

// ── Modal ────────────────────────────────────────────────────────────────────

function showModal(title, value, onConfirm, multiline) {
  const root = document.getElementById("modal-root");
  const inputTag = multiline ? "textarea" : "input";
  root.innerHTML =
    '<div class="modal-overlay" onclick="closeModal()">' +
    '  <div class="modal" onclick="event.stopPropagation()">' +
    "    <h3>" + esc(title) + "</h3>" +
    "    <" + inputTag + ' id="modal-input" placeholder="...">' + (multiline ? esc(value) + "</textarea>" : "") +
    '    <div class="modal-btns">' +
    '      <button class="cancel" onclick="closeModal()">Cancel</button>' +
    '      <button class="confirm" id="modal-confirm">Save</button>' +
    "    </div>" +
    "  </div>" +
    "</div>";
  if (!multiline) document.getElementById("modal-input").value = value;
  document.getElementById("modal-confirm").onclick = () => {
    const v = document.getElementById("modal-input").value;
    closeModal();
    onConfirm(v);
  };
}

function closeModal() {
  document.getElementById("modal-root").innerHTML = "";
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ── Init ─────────────────────────────────────────────────────────────────────

addBubble("assistant",
  "Hi! I'm Kindling, your dating assistant.\n\n" +
  "I can help with message ideas, conversation tips, icebreakers " +
  "for apps or in-person, and date suggestions.\n\n" +
  "Tap the gear to choose your AI provider and add an API key " +
  "(Gemini has a free tier), then ask me anything!");

// Register service worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/kindling/sw.js", { scope: "/kindling/" });
}
