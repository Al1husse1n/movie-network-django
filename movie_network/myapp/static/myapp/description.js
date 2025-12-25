document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("watchlistBtn");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const added = btn.classList.toggle("added");
    btn.setAttribute("aria-pressed", added ? "true" : "false");

    btn.querySelector(".watchlist-text").textContent =
      added ? "Saved to Watchlist" : "Add to Watchlist";

    btn.querySelector(".watchlist-icon").textContent =
      added ? "✓" : "+";

    // future: send fetch request to Django backend
  });
});
