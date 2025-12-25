/*
  watchlist.js
  -------------
  Handles:
  - Rendering watchlist items
  - Removing items
  - Empty watchlist state
*/

// Sample watchlist data (can later come from API or localStorage)
let watchlist = [
  {
    id: 1,
    title: "Inception",
    rating: "⭐ 8.8",
    poster: "https://via.placeholder.com/300x450"
  },
  {
    id: 2,
    title: "Interstellar",
    rating: "⭐ 8.6",
    poster: "https://via.placeholder.com/300x450"
  },
  {
    id: 3,
    title: "The Dark Knight",
    rating: "⭐ 9.0",
    poster: "https://via.placeholder.com/300x450"
  }
];

const grid = document.getElementById("watchlistGrid");
const emptyState = document.getElementById("emptyState");

/* Render watchlist items */
function renderWatchlist() {
  grid.innerHTML = "";

  // Show empty state if no items
  if (watchlist.length === 0) {
    emptyState.classList.remove("d-none");
    return;
  }

  emptyState.classList.add("d-none");

  watchlist.forEach(item => {
    const card = document.createElement("div");
    card.className = "col-6 col-md-4 col-lg-3";

    card.innerHTML = `
      <div class="watchlist-card h-100">
        <img
          src="${item.poster}"
          alt="${item.title} poster"
          class="watchlist-poster"
        />
        <div class="card-body d-flex flex-column">
          <h6 class="watchlist-title mb-1">${item.title}</h6>
          <span class="watchlist-rating mb-3">${item.rating}</span>
          <button
            class="btn btn-sm remove-btn mt-auto"
            onclick="removeFromWatchlist(${item.id})">
            Remove
          </button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

/* Remove item from watchlist */
function removeFromWatchlist(id) {
  watchlist = watchlist.filter(item => item.id !== id);
  renderWatchlist();
}

/* Initial render */
renderWatchlist();
