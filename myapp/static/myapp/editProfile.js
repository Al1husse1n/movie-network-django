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
    const topListForm = document.getElementById('topListsForm');
    // keep track of autocomplete inputs/results for global hide behaviour
    const _autocompleteInputs = [];
    const _autocompleteResults = [];
    let _globalAutocompleteListenersAdded = false;


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
        .then(response =>{
            if(response.status == 404){
                return {};
            }
            return response.json()
            .then(parsedResponse =>{
                if(response.status == 500){
                   alert(parsedResponse.error);
                    return {};
                }
                else{
                    return parsedResponse;
                }
            })
        });
    };

    // Helper to attach fetch-backed autocomplete (uses provided fetcher)
    function attachFetchAutocomplete(inputEl, resultEl, fetcher) {
        if (!inputEl || !resultEl || typeof fetcher !== 'function') return;
        resultEl.style.display = 'none';
        // register elements for global click/escape handling
        _autocompleteInputs.push(inputEl);
        _autocompleteResults.push(resultEl);
        // add global listeners once
        if (!_globalAutocompleteListenersAdded) {
            _globalAutocompleteListenersAdded = true;
            // hide when pressing Escape
            document.addEventListener('keydown', (ev) => {
                if (ev.key === 'Escape') {
                    _autocompleteResults.forEach(r => { if (r) r.style.display = 'none'; });
                }
            });
            // hide when clicking outside any registered input/result
            document.addEventListener('click', (ev) => {
                const t = ev.target;
                for (const inp of _autocompleteInputs) {
                    if (inp && inp.contains && inp.contains(t)) return;
                }
                for (const res of _autocompleteResults) {
                    if (res && res.contains && res.contains(t)) return;
                }
                _autocompleteResults.forEach(r => { if (r) r.style.display = 'none'; });
            });
        }
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
                            inputEl.name = k;
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
        // also hide on Escape when this input has focus
        inputEl.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') {
                resultEl.style.display = 'none';
            }
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

    // capture initial values (name and value) so we can skip unchanged updates
    const _initialTop = { movies: {}, shows: {} };
    for (let i = 1; i <= 5; i++) {
        const m = document.getElementById(`top_movies_${i}`);
        const s = document.getElementById(`top_shows_${i}`);
        _initialTop.movies[i] = { name: m && m.name ? String(m.name) : '', value: m && m.value ? m.value.trim() : '' };
        _initialTop.shows[i] = { name: s && s.name ? String(s.name) : '', value: s && s.value ? s.value.trim() : '' };
    }
    const _initialWeekly = weeklyInput ? { name: weeklyInput.name ? String(weeklyInput.name) : '', value: weeklyInput.value ? weeklyInput.value.trim() : '' } : { name: '', value: '' };

    // keep weekly behavior but ensure encoding and empty-check (existing fetch)
    let timeout; // for debounce
    if (weeklyInput && weeklyResult) {
        weeklyResult.style.display = 'none';
        // register weekly pick autocomplete elements to global handlers
        _autocompleteInputs.push(weeklyInput);
        _autocompleteResults.push(weeklyResult);
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
                        const id = key;
                        console.log(text);
                        const li = document.createElement('li');
                        li.textContent = text;
                        li.id = id;
                        li.tabIndex = 0;
                        li.addEventListener('click', () => {
                            weeklyInput.value = text;
                            weeklyInput.name = id;
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
        weeklyInput.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') {
                weeklyResult.style.display = 'none';
            }
        });
    };

    function update_top_5(type, id, name, rank){
        return fetch('/updateTop5/',{
            method: 'PUT',
            headers: {
            "Content-Type": "application/json",
            },
            body:JSON.stringify({
                type: type,
                result:{
                    id:id,
                    name:name,
                    rank: rank
                }
            })
        })
        .then(response => {
            const data = response;
            return response.json()
            .then(parsedResponse => {
                if(!data.ok){
                    alert(parsedResponse.error);
                }
                else{
                    console.log(parsedResponse.message);
                }
            });
        });
    };

    function update_wp(name, id){
        return fetch('/updateWP/',{
            method: 'PUT',
            headers: {
            "Content-Type": "application/json",
            },
            body:JSON.stringify({
                result:{
                    id:id,
                    name:name
                }
            })
        })
        .then(response => {
            const data = response;
            return response.json()
            .then(parsedResponse => {
                if(!data.ok){
                    console.log(parsedResponse.error);
                }
                else{
                    console.log(parsedResponse.message);
                }
            });
        });
    };

    topListForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        // update weekly pick only if changed
        if (weeklyInput) {
            const currentWeekly = { name: weeklyInput.name ? String(weeklyInput.name) : '', value: weeklyInput.value ? weeklyInput.value.trim() : '' };
            if (currentWeekly.name !== _initialWeekly.name || currentWeekly.value !== _initialWeekly.value) {
                const wp_id = currentWeekly.name === "" || currentWeekly.value === "" ? 0 : parseInt(currentWeekly.name);
                const wp_title = weeklyInput.value;
                await update_wp(wp_title, wp_id);
            }
        }

        // update each top movie/show only if changed relative to initial capture
        for (let i = 1; i < 6; i++) {
            const movieInput = document.getElementById(`top_movies_${i}`);
            if (movieInput) {
                const currentMovie = { name: movieInput.name ? String(movieInput.name) : '', value: movieInput.value ? movieInput.value.trim() : '' };
                const initialMovie = _initialTop.movies[i] || { name: '', value: '' };
                if (currentMovie.name !== initialMovie.name || currentMovie.value !== initialMovie.value) {
                    const movie_id = currentMovie.name === "" || currentMovie.value === "" ? 0 : parseInt(currentMovie.name);
                    const movie_title = movieInput.value;
                    await update_top_5('movie', movie_id, movie_title, i);
                }
            }

            const showInput = document.getElementById(`top_shows_${i}`);
            if (showInput) {
                const currentShow = { name: showInput.name ? String(showInput.name) : '', value: showInput.value ? showInput.value.trim() : '' };
                const initialShow = _initialTop.shows[i] || { name: '', value: '' };
                if (currentShow.name !== initialShow.name || currentShow.value !== initialShow.value) {
                    const show_id = currentShow.name === "" || currentShow.value === "" ? 0 : parseInt(currentShow.name);
                    const show_name = showInput.value;
                    await update_top_5('show', show_id, show_name, i);
                }
            }
        }

    });


});
