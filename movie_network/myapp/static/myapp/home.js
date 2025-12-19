// changed: wrap initialization so all DOM elements exist and errors don't prevent the menuToggle handler
document.addEventListener('DOMContentLoaded', () => {
    // Composer character counter
    const composeInput = document.getElementById('composeInput');
    const charCount = document.getElementById('charCount');
    const timeline = document.querySelector("#timeline");

    if (composeInput) {
        composeInput.addEventListener('input', () => {
            const remaining = composeInput.maxLength - composeInput.value.length;
            charCount.textContent = remaining;
            if (remaining < 20) charCount.style.color = '#ffa726';
            else charCount.style.color = 'var(--muted)';
            if (remaining < 0) charCount.style.color = '#ff4444';
        });
    }

    // guard other elements before attaching listeners
    const dropdown = document.querySelector('.community-dropdown select');
    if (dropdown) {
        dropdown.addEventListener('mouseenter', () => dropdown.style.transform = 'translateY(-1px)');
        dropdown.addEventListener('mouseleave', () => dropdown.style.transform = 'translateY(0)');
        dropdown.addEventListener('focus', () => document.querySelector('.community-dropdown').style.zIndex = '10');
        dropdown.addEventListener('blur', () => document.querySelector('.community-dropdown').style.zIndex = '1');
    }

    const composeForm = document.getElementById('composeForm');
    if (composeForm) {
        composeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const content = (document.getElementById('composeInput')?.value || '').trim();
            const communityId = document.getElementById("communitySelect")?.value;
            const spoilerChecked = document.getElementById('spoiler')?.checked || false;
            if (!content) {
                const el = document.getElementById('composeInput');
                if (el) { el.style.borderColor = '#ff4444'; setTimeout(()=> el.style.borderColor = 'rgba(255,255,255,0.03)',2000); }
                return;
            }
            fetch('/compose/',{
                method:'POST',
                credentials: 'same-origin',
                headers: {
                  "Content-Type": "application/json",
                  "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                body: JSON.stringify({ content, communityId, spoiler: spoilerChecked })
            })
            .then(response => response.json())
            .then(result => {
                const ci = document.getElementById('composeInput');
                if (ci) ci.value = "";
                if (!result.error && communityId) loadCommunityPosts(communityId);
            })
            .catch(err => console.error(err));
        });
    }

    // community change handler (guarded)
    const communitySelect = document.getElementById('communitySelect');
    if (communitySelect) communitySelect.addEventListener('change', function() { loadCommunityPosts(this.value); });

    // mobile aside toggle (guarded)
    const menuToggle = document.getElementById('menuToggle');
    const mobileAside = document.getElementById('mobile-aside');
    const overlay = document.getElementById('asideOverlay');
    if (menuToggle && mobileAside && overlay) {
        const openAside = () => { mobileAside.classList.add('open'); overlay.classList.add('visible'); menuToggle.setAttribute('aria-expanded','true'); overlay.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; };
        const closeAside = () => { mobileAside.classList.remove('open'); overlay.classList.remove('visible'); menuToggle.setAttribute('aria-expanded','false'); overlay.setAttribute('aria-hidden','true'); document.body.style.overflow=''; };
        menuToggle.addEventListener('click', () => mobileAside.classList.contains('open') ? closeAside() : openAside());
        overlay.addEventListener('click', closeAside);
        document.addEventListener('keydown', e => { if (e.key === 'Escape' && mobileAside.classList.contains('open')) closeAside(); });
        mobileAside.addEventListener('click', e => { if (e.target.tagName === 'A') closeAside(); });
    }

}); // end DOMContentLoaded wrapper

function loadCommunityPosts(communityId) {
    const timeline = document.getElementById('timeline');
    timeline.innerHTML = '<div class="loading">Loading posts...</div>';

    fetch(`/${communityId}/get`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(posts => {
        timeline.innerHTML = '';
        if(posts && Object.keys(posts).length > 0){
            for(let postId in posts){
                const post = posts[postId];
                timeline.innerHTML += `
                    <article class="tweet card">
                        <div class="tweet-left">
                            <div class="t-avatar">${post.poster_username}</div>
                        </div>
                        <div class="tweet-body">
                            <div class="tweet-head">
                                <span class="t-name">${ post.poster_username }</span>
                                <span class="t-handle">@${ post.poster_username}</span>
                                <span class="t-time">· ${ post.post_time }</span>
                            </div>
                            <div class="t-text">${ post.content }</div>
                        </div>
                    </article>
                `;
            }
        }
        else{
            timeline.innerHTML = `
                <p class="muted">No posts yet. Select another community or compose one above!</p>
            `;
        }
    })
    .catch(error => {
        if (error.message.includes('404')) {
            timeline.innerHTML = `
                <div class="alert alert-error">
                    <strong>Community Not Found</strong>
                    <p>The selected community could not be found.</p>
                </div>
            `;
        }
        else if (error.message.includes('500')) {
            timeline.innerHTML = `
                <div class="alert alert-error">
                    <strong>Server Error</strong>
                    <p>Something went wrong on our end. Please try again later.</p>
                </div>
            `;
        }
        else {
            timeline.innerHTML = `
                <div class="alert alert-error">
                    <strong>Error Loading Posts</strong>
                    <p>${error.message}</p>
                </div>
            `;
        }
    });
}

