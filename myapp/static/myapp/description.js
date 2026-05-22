document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementsByClassName("watchlist-btn")[0];
  const poster = document.getElementsByClassName("movie-poster")[0];

  if (!btn || !poster) return;

  const movieID = poster.id;

  btn.addEventListener("click", () => {
    let payload = null;

    if (btn.id === "movieWatchlist") {
      payload = { type: "movie", movie_id: movieID };
    } else if (btn.id === "showWatchlist") {
      payload = { type: "show", show_id: movieID };
    } else {
      return;
    }

    fetch("/updateWatchlist/", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((response) => {
        return response.json().then((parsedResponse) => {
          if (response.status === 400) {
            alert(parsedResponse.error);
            return;
          } else if (response.status === 500) {
            alert("Something wrong happened, try again");
            console.error(parsedResponse.error);
            return;
          } else if (response.ok) {
            const added = btn.classList.toggle("added");
            btn.setAttribute("aria-pressed", added ? "true" : "false");

            btn.querySelector(".watchlist-text").textContent =
              added ? "Saved to Watchlist" : "Add to Watchlist";

            btn.querySelector(".watchlist-icon").textContent =
              added ? "✓" : "+";

            console.log(parsedResponse.message);
          }
        });
      })
      .catch((error) => {
        alert("Something wrong happened, try again");
        console.error(error);
      });
  });
});
