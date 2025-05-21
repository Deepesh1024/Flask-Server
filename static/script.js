document.addEventListener('DOMContentLoaded', () => {
    const youtubeInput = document.getElementById('youtube_url');
    const fileInput = document.getElementById('video_file');
    const presentationSwitch = document.getElementById('presentationSwitch');
    const presentationLabel = document.getElementById('presentationLabel');
    const form = document.getElementById('analysisForm');
    const submitBtn = document.getElementById('submitBtn');
    const messageDiv = document.getElementById('message');
    const downloadLink = document.getElementById('downloadLink');

    // Function to toggle Presentation Mode text
    function togglePresentation() {
        const isPresentationMode = presentationSwitch.checked;
        presentationLabel.textContent = isPresentationMode ? 'Presentation Mode' : 'Resume Mode';
    }

    // Video URL validation for YouTube and Google Drive
    function isValidVideoURL(url) {
        const youtubePattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/(watch\?v=)?([a-zA-Z0-9_-]{11}).*$/;
        const drivePattern = /^(https?:\/\/)?(drive\.google\.com\/file\/d\/[a-zA-Z0-9_-]+\/view).*$/;
        return youtubePattern.test(url) || drivePattern.test(url);
    }

    // Validate YouTube or Google Drive URL on input change
    youtubeInput.addEventListener("input", function () {
        if (this.value && !isValidVideoURL(this.value)) {
            this.setCustomValidity("Please enter a valid YouTube or Google Drive video link.");
        } else {
            this.setCustomValidity("");
        }
    });

    // Form submission handling
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Validate inputs
        if (!youtubeInput.value.trim() && !fileInput.files.length) {
            showMessage('Please provide a YouTube/Google Drive URL or upload a video file.', 'text-danger');
            return;
        }

        const formData = new FormData(form);
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
                showMessage(result.message || 'An error occurred', 'text-danger');
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
        messageDiv.className = `mt-3 text-center ${className}`;
        messageDiv.classList.remove('d-none');
    }

    // Event Listeners
    presentationSwitch.addEventListener('change', togglePresentation);
    togglePresentation();
});