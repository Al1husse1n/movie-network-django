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

});