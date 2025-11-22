// Composer character counter
const composeInput = document.getElementById('composeInput');
const charCount = document.getElementById('charCount');

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

// Auto-submit when selecting community
const communitySelect = document.getElementById('communitySelect');
communitySelect.addEventListener('change', () => {
    document.getElementById('communityForm').submit();
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
    if (content.length === 0) {
        e.preventDefault();
        composeInput.style.borderColor = '#ff4444';
        setTimeout(() => {
            composeInput.style.borderColor = 'rgba(255,255,255,0.03)';
        }, 2000);
    }
});