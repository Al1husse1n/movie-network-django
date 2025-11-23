// Composer character counter
const composeInput = document.getElementById('composeInput');
const charCount = document.getElementById('charCount');
const timeline = document.querySelector("#timeline")

composeInput.addEventListener('input', () => {
    const remaining = composeInput.maxLength - composeInput.value.length;
    charCount.textContent = remaining;
    
    if(remaining < 20) {
        charCount.style.color = '#ffa726'; // Orange warning
    } else {
        charCount.style.color = 'var(--muted)';
    }
    
    if(remaining < 0) {
        charCount.style.color = '#ff4444'; // Red when over limit
    }
});


// Enhanced dropdown interactions
const dropdown = document.querySelector('.community-dropdown select');

dropdown.addEventListener('mouseenter', () => {
    dropdown.style.transform = 'translateY(-1px)';
});

dropdown.addEventListener('mouseleave', () => {
    dropdown.style.transform = 'translateY(0)';
});

// Add focus effect for accessibility
dropdown.addEventListener('focus', () => {
    document.querySelector('.community-dropdown').style.zIndex = '10';
});

dropdown.addEventListener('blur', () => {
    document.querySelector('.community-dropdown').style.zIndex = '1';
});

// Form submission enhancement
document.getElementById('composeForm').addEventListener('submit', function(e) {
    const content = composeInput.value.trim();
    const communityId = document.getElementById("communitySelect").value;
    if (content.length === 0) {
        e.preventDefault();
        composeInput.style.borderColor = '#ff4444';
        setTimeout(() => {
            composeInput.style.borderColor = 'rgba(255,255,255,0.03)';
        }, 2000);
    }
    else{
        e.preventDefault(); 
        fetch('/compose/',{
            method:'POST',
            credentials: 'same-origin',
            body: JSON.stringify({
                content:content,
                communityId:communityId
            })
        })
        .then(response => response.json())
        .then(result =>{
            composeInput.value="";
            if(result.error){
                console.log(result.error)
            }
            
        })
    }
});

    document.getElementById('communitySelect').addEventListener('change',function(event){
        const communityId = this.value;
        timeline.innerHTML = '<div class="loading">Loading posts...</div>';
        fetch(`/${communityId}/get`)
        .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
        .then(posts =>{
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
                    `
            }
            }
            else{
                timeline.innerHTML = `
                    <p class="muted">No posts yet. Select another community or compose one above!</p>
                `
            }
        })
        .catch(error=>{
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
    });

