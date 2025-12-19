// script.js

// Simple JavaScript for future interactivity (e.g., dynamic posts, buttons)

// Example: Make Edit Profile button alert (customize as needed)
document.querySelector('.edit-profile-btn').addEventListener('click', function(e) {
    e.preventDefault();
    alert('Edit Profile functionality - add your logic here!');
});

// Example: Watchlist button
document.querySelector('.watchlist-btn').addEventListener('click', function(e) {
    e.preventDefault();
    alert('Opening Watchlist - customize this link or modal!');
});

// You can add more JS for loading posts dynamically, etc.
// For example, fetch from an API or local storage.
console.log('GreenBird Profile Page Loaded');