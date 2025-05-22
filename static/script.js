document.addEventListener('DOMContentLoaded', () => {
    const driveSource = document.getElementById('driveSource');
    const fileSource = document.getElementById('fileSource');
    const driveSection = document.getElementById('driveSection');
    const fileSection = document.getElementById('fileSection');
    const driveInput = document.getElementById('drive_url');
    const fileInput = document.getElementById('video_file');
    const presentationSwitch = document.getElementById('presentationSwitch');
    const presentationLabel = document.getElementById('presentationLabel');
    const form = document.getElementById('analysisForm');
    const submitBtn = document.getElementById('submitBtn');
    const messageDiv = document.getElementById('message');
    const downloadLink = document.getElementById('downloadLink');

    // Function to toggle between Google Drive URL and File Upload
    function toggleSource() {
        const isFileSource = fileSource.checked;
        driveSection.classList.toggle('d-none', isFileSource);
        fileSection.classList.toggle('d-none', !isFileSource);
        driveInput.required = !isFileSource;
        fileInput.required = isFileSource;
    }

    // Function to toggle Presentation Mode text
    function togglePresentation() {
        const isPresentationMode = presentationSwitch.checked;
        presentationLabel.textContent = isPresentationMode ? 'Presentation Mode' : 'Resume Mode';
    }

    // Video URL validation for Google Drive
    function isValidVideoURL(url) {
        const drivePattern = /^(https?:\/\/)?(drive\.google\.com\/file\/d\/[a-zA-Z0-9_-]+\/view).*$/;
        return drivePattern.test(url);
    }

    // Validate Google Drive URL on input change
    driveInput.addEventListener('input', function () {
        if (this.value && !isValidVideoURL(this.value)) {
            this.setCustomValidity('Please enter a valid Google Drive video link.');
        } else {
            this.setCustomValidity('');
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
    
        const userName = document.getElementById('user_name').value.trim();
        if (!userName) {
            showMessage('Please enter your name.', 'text-danger');
            return;
        }
    
        if (driveSource.checked && !driveInput.value.trim()) {
            showMessage('Please provide a Google Drive URL.', 'text-danger');
            return;
        }
    
        if (driveSource.checked && !isValidVideoURL(driveInput.value)) {
            showMessage('Please provide a valid Google Drive video link.', 'text-danger');
            return;
        }
    
        if (fileSource.checked && !fileInput.files.length) {
            showMessage('Please upload a video file.', 'text-danger');
            return;
        }
    
        const formData = new FormData(form);
        console.log('FormData contents:');
        for (let [key, value] of formData.entries()) {
            console.log(`${key}: ${value}`);
        }
    
        submitBtn.disabled = true;
        submitBtn.textContent = 'Analyzing...';
        showMessage('Processing video, please wait...', 'text-muted');
    
        try {
            const response = await fetch('/dashboard', {
                method: 'POST',
                body: formData
            });
    
            const result = await response.json();
    
            if (response.ok) {
                showMessage(result.message, 'text-success');
                downloadLink.classList.remove('d-none');
                downloadLink.href = '/download_pdf';
            } else {
                showMessage(result.error || 'An error occurred', 'text-danger');
            }
        } catch (error) {
            showMessage('An error occurred: ' + error.message, 'text-danger');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Analysis';
        }
    });

    // Function to show messages
    function showMessage(text, className) {
        messageDiv.textContent = text;
        messageDiv.className = `mt-4 text-center ${className}`;
        messageDiv.classList.remove('d-none');
    }

    // Event Listeners
    driveSource.addEventListener('change', toggleSource);
    fileSource.addEventListener('change', toggleSource);
    presentationSwitch.addEventListener('change', togglePresentation);
    toggleSource();
    togglePresentation();

    // Inline CSS for dynamic hover effects
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('mouseenter', () => {
            link.style.color = '#f472b6';
            link.style.transform = 'scale(1.05)';
        });
        link.addEventListener('mouseleave', () => {
            link.style.color = '#ffffff';
            link.style.transform = 'scale(1)';
        });
    });

    const card = document.querySelector('.card');
    card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-5px)';
    });
    card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0)';
    });

    const inputs = document.querySelectorAll('.form-control');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            input.style.borderColor = '#3b82f6';
            input.style.boxShadow = '0 0 0 0.25rem rgba(59, 130, 246, 0.25)';
        });
        input.addEventListener('blur', () => {
            input.style.borderColor = '#1e40af';
            input.style.boxShadow = 'none';
        });
    });

    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.03)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
        });
    });
});