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

    // Posts "Load more" behavior: show 5 posts initially, reveal 5 more per click
    const postsContainer = document.getElementById('postsContainer');
    const loadMoreBtn = document.getElementById('loadMorePosts');
    const showLessBtn = document.getElementById('showLessPosts');
    if (postsContainer && loadMoreBtn && showLessBtn) {
        const posts = Array.from(postsContainer.querySelectorAll('.post'));
        const pageSize = 5;
        let shown = Math.min(pageSize, posts.length);

        function updateVisibility() {
            posts.forEach((p, i) => p.classList.toggle('hidden', i >= shown));
            // load more visible when there are hidden posts
            loadMoreBtn.style.display = (shown < posts.length) ? 'inline-block' : 'none';
            // show less visible only when we've expanded beyond the initial page
            showLessBtn.style.display = (shown > pageSize) ? 'inline-block' : 'none';
        }

        // initialize
        updateVisibility();

        loadMoreBtn.addEventListener('click', function(e) {
            e.preventDefault();
            shown = Math.min(posts.length, shown + pageSize);
            updateVisibility();
        });

        showLessBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // decrease shown by pageSize but keep at least one page
            shown = Math.max(pageSize, shown - pageSize);
            updateVisibility();
            // scroll the container into view so user sees the top of the posts
            postsContainer.scrollIntoView({ behavior: 'smooth' });
        });
    }
});
