import test from "node:test";
import assert from "node:assert/strict";
import { renderCard, renderMessage } from "../static/chat.js";

test("renderCard includes name, cuisine, budget, location", () => {
  const html = renderCard({
    name: "Pasta Palace", cuisine: "italian", budget: "mid",
    location: "downtown", rating: 4.5,
  });
  assert.ok(html.includes("Pasta Palace"));
  assert.ok(html.includes("italian"));
  assert.ok(html.includes("mid"));
  assert.ok(html.includes("downtown"));
});

test("renderMessage embeds cards only when candidates are given", () => {
  const withCards = renderMessage("assistant", "Here you go", [
    { name: "A", cuisine: "x", budget: "mid", location: "y", rating: 4 },
  ]);
  assert.ok(withCards.includes("restaurant-card"));

  const withoutCards = renderMessage("user", "hello");
  assert.ok(!withoutCards.includes("restaurant-card"));
});

test("renderMessage escapes HTML in user text to prevent XSS", () => {
  const html = renderMessage("user", "<script>alert(1)</script>");
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});
