// script.js

// Mobile menu toggle + safe handlers for profile actions
document.addEventListener('DOMContentLoaded', function() {
    const menuBtn = document.getElementById('menuToggle');
    const sidebar = document.querySelector('.sidebar-left');
    const overlay = document.getElementById('asideOverlay');

    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const isOpen = sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('visible', isOpen);
            menuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    }

    if (overlay && sidebar) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            overlay.classList.remove('visible');
            if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
        });
    }

    // Close with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('visible');
            if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
        }
    });

});
