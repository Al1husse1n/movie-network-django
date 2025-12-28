document.addEventListener('DOMContentLoaded', () => {
    
    // Select Elements
    const editForm = document.getElementById('editProfileForm');
    const usernameInput = document.getElementById('username');
    const usernameError = document.getElementById('usernameError');
    const bioInput = document.getElementById('bio');
    const bioError = document.getElementById('bioError');
    const fileInput = document.getElementById('profilePic');
    const previewImg = document.getElementById('previewImg');
    const cancelBtn = document.getElementById('cancelBtn');
    const weeklyResult = document.getElementById('weekly-result'); 
    const weeklyInput = document.getElementById('weekly_pick');
    

    // hide result container when empty
    if (weeklyResult) {
        weeklyResult.style.display = 'none';
    }

    // 1. LIVE IMAGE PREVIEW
    // Fires when the user selects a new file
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                // Set the preview image src to the file's data URL
                previewImg.setAttribute('src', e.target.result);
            }
            
            reader.readAsDataURL(file);
        }
    });


    editForm.addEventListener('submit', (e) => {
        // Reset error state
        usernameError.innerHTML = "Username is required.";
        usernameError.classList.add('d-none');
        usernameInput.classList.remove('border-danger');
        bioError.classList.add('d-none');
        bioInput.classList.remove('border-danger');
        e.preventDefault();
        if (usernameInput.value.trim() === "") {
            usernameError.classList.remove('d-none');
            usernameInput.classList.add('border-danger');
            usernameInput.focus();
            return;
        }
        else{
            fetch('/changeprofile/',{
                method:'PUT',
                headers: {
                    'Content-Type': 'application/json' 
                },
                body:JSON.stringify({
                    username:usernameInput.value,
                    bio:bioInput.value
                })
            })
            .then(async response =>{
                const data = await response.json();
                if(response.status === 400){
                    if(data.errors.username){
                        usernameError.innerHTML = `${data.errors.username}`;
                        usernameError.classList.remove('d-none');
                        usernameInput.classList.add('border-danger');
                    }
                    else if(data.errors.bio){
                        bioError.classList.remove('d-none');
                        bioInput.classList.add('border-danger');
                    }
                    else{
                        console.error(data.errors);
                    }
                }
                else if(!response.ok){
                    throw new Error("Request failed with status " + response.status + data);
                }
                else{
                    editForm.submit();
                }
            })
            .catch(error =>{
                console.error("Network or server error", error);
            })
        }
        
    });


    cancelBtn.addEventListener('click', () => {
            window.location.reload(); 
    });

    function getMovieByName(name){          //return 5 movies that matches the substring
        // encode the name to avoid server errors for special characters
        return fetch(`/searchMovie/${encodeURIComponent(name)}`)
        .then(response => response.json())
        .then(response =>{
            if(response.status == 404){
                return {};
            }
            else if(response.status == 500){
                alert(response.error);
                return {};
            }
            else{
                return response;
            }
        });
    };

    function getShowByName(name){          //return 5 movies that matches the substring
        // encode the name to avoid server errors for special characters
        return fetch(`/searchShow/${encodeURIComponent(name)}`)
        .then(response => response.json())
        .then(response =>{
            if(response.status == 404){
                return {};
            }
            else if(response.status == 500){
                alert(response.error);
                return {};
            }
            else{
                return response;
            }
        });
    };

    // Helper to attach fetch-backed autocomplete (uses provided fetcher)
    function attachFetchAutocomplete(inputEl, resultEl, fetcher) {
        if (!inputEl || !resultEl || typeof fetcher !== 'function') return;
        resultEl.style.display = 'none';
        let t;
        inputEl.addEventListener('keyup', () => {
            clearTimeout(t);
            t = setTimeout(async () => {
                const q = inputEl.value.trim();
                if (!q) {
                    resultEl.innerHTML = '';
                    resultEl.style.display = 'none';
                    return;
                }
                try {
                    const items = await fetcher(q);
                    resultEl.innerHTML = '';
                    let count = 0;
                    for (let k in items) {
                        const text = items[k];
                        const li = document.createElement('li');
                        li.textContent = text;
                        li.tabIndex = 0;
                        li.addEventListener('click', () => {
                            inputEl.value = text;
                            resultEl.innerHTML = '';
                            resultEl.style.display = 'none';
                        });
                        li.addEventListener('keydown', (ev) => {
                            if (ev.key === 'Enter') {
                                ev.preventDefault();
                                li.click();
                            }
                        });
                        resultEl.appendChild(li);
                        count++;
                    }
                    resultEl.style.display = count > 0 ? 'block' : 'none';
                } catch (err) {
                    console.error('autocomplete fetch error', err);
                    resultEl.innerHTML = '';
                    resultEl.style.display = 'none';
                }
            }, 300);
        });
    }

    // attach fetch-backed autocomplete to top shows and movies inputs
    for (let i = 1; i <= 5; i++) {
        const showInput = document.getElementById(`top_shows_${i}`);
        const showResult = document.getElementById(`show-result-${i}`);
        attachFetchAutocomplete(showInput, showResult, getShowByName);

        const movieInput = document.getElementById(`top_movies_${i}`);
        const movieResult = document.getElementById(`movie-result-${i}`);
        attachFetchAutocomplete(movieInput, movieResult, getMovieByName);
    }

    // keep weekly behavior but ensure encoding and empty-check (existing fetch)
    let timeout; // for debounce
    if (weeklyInput && weeklyResult) {
        weeklyResult.style.display = 'none';
        weeklyInput.addEventListener('keyup', () => {
            clearTimeout(timeout);
            timeout = setTimeout(async () => {
                const q = weeklyInput.value.trim();
                if (!q) {
                    weeklyResult.innerHTML = "";
                    weeklyResult.style.display = 'none';
                    return;
                }
                try {
                    const movies = await getMovieByName(q);
                    weeklyResult.innerHTML = "";
                    let count = 0;
                    for (let key in movies) {
                        const text = movies[key];
                        console.log(text);
                        const li = document.createElement('li');
                        li.textContent = text;
                        li.tabIndex = 0;
                        li.addEventListener('click', () => {
                            weeklyInput.value = text;
                            weeklyResult.innerHTML = '';
                            weeklyResult.style.display = 'none';
                        });
                        li.addEventListener('keydown', (ev) => {
                            if (ev.key === 'Enter') {
                                ev.preventDefault();
                                li.click();
                            }
                        });
                        weeklyResult.appendChild(li);
                        count++;
                    }
                    weeklyResult.style.display = count > 0 ? 'block' : 'none';
                } catch (err) {
                    console.error('search fetch error', err);
                    weeklyResult.innerHTML = '';
                    weeklyResult.style.display = 'none';
                }
            }, 300);
        });
    }


});