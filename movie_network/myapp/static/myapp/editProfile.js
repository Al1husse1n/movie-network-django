document.addEventListener('DOMContentLoaded', () => {
    
    // Select Elements
    const editForm = document.getElementById('editProfileForm');
    const usernameInput = document.getElementById('username');
    const usernameError = document.getElementById('usernameError');
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

    // 2. FORM VALIDATION & SUBMISSION
    editForm.addEventListener('submit', (e) => {
        e.preventDefault(); // Prevent page refresh

        // Reset error state
        usernameError.classList.add('d-none');
        usernameInput.classList.remove('border-danger');

        // Validation: Check if username is empty
        if (usernameInput.value.trim() === "") {
            usernameError.classList.remove('d-none');
            usernameInput.classList.add('border-danger');
            usernameInput.focus();
            return;
        }

        // Logic for "Saving" (In a real app, this would be an API call)
        alert("Changes saved successfully!");
        console.log("Updated Username:", usernameInput.value);
        console.log("Updated Bio:", document.getElementById('bio').value);
    });

    // 3. CANCEL BUTTON LOGIC
    cancelBtn.addEventListener('click', () => {
        if (confirm("Are you sure you want to discard changes?")) {
            // Simply refresh or redirect back to profile
            window.location.reload(); 
        }
    });

});