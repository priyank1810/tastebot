function esc(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function renderCard(restaurant) {
  const stars = restaurant.rating ? "★".repeat(Math.round(restaurant.rating)) : "";
  return `
    <div class="restaurant-card">
      <div class="card-name">${esc(restaurant.name)}</div>
      <div class="card-meta">${esc(restaurant.cuisine)} · ${esc(restaurant.budget)} · ${esc(restaurant.location)}</div>
      <div class="card-rating">${stars} ${esc(restaurant.rating ?? "")}</div>
    </div>
  `;
}

export function renderMessage(role, text, candidates = []) {
  const cards = candidates.map(renderCard).join("");
  return `
    <div class="message ${esc(role)}">
      <div class="bubble">${esc(text)}</div>
      ${cards ? `<div class="cards">${cards}</div>` : ""}
    </div>
  `;
}

function initChat() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const messages = document.getElementById("messages");
  let sessionId = null;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    messages.innerHTML += renderMessage("user", text);
    input.value = "";

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await res.json();
    sessionId = data.session_id;
    messages.innerHTML += renderMessage("assistant", data.reply, data.candidates);
    messages.scrollTop = messages.scrollHeight;
  });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initChat);
}
