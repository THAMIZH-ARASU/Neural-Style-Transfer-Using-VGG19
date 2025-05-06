/* app/frontend/static/js/script.js */

document.addEventListener('DOMContentLoaded', () => {
    // Theme toggle
    const themeSwitch = document.getElementById('theme-switch');
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeSwitch.checked = true;
    }

    themeSwitch.addEventListener('change', () => {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', themeSwitch.checked ? 'dark' : 'light');
    });

    // Image upload handling
    const contentInput = document.getElementById('content-input');
    const styleInput = document.getElementById('style-input');
    const contentPreview = document.getElementById('content-preview');
    const stylePreview = document.getElementById('style-preview');
    const contentPreviewContainer = document.getElementById('content-preview-container');
    const stylePreviewContainer = document.getElementById('style-preview-container');
    const removeContentBtn = document.getElementById('remove-content-btn');
    const removeStyleBtn = document.getElementById('remove-style-btn');
    const uploadBtn = document.getElementById('upload-btn');
    let contentFile, styleFile, contentId, styleId;

    function updateUploadButtonState() {
        uploadBtn.disabled = !(contentFile && styleFile);
    }

    function handleImagePreview(input, preview, previewContainer) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.src = e.target.result;
                previewContainer.style.display = 'block';
                input.closest('.upload-area').querySelector('.upload-instructions').style.display = 'none';
            };
            reader.readAsDataURL(input.files[0]);
        }
    }

    contentInput.addEventListener('change', () => {
        contentFile = contentInput.files[0];
        handleImagePreview(contentInput, contentPreview, contentPreviewContainer);
        updateUploadButtonState();
    });

    styleInput.addEventListener('change', () => {
        styleFile = styleInput.files[0];
        handleImagePreview(styleInput, stylePreview, stylePreviewContainer);
        updateUploadButtonState();
    });

    removeContentBtn.addEventListener('click', () => {
        contentInput.value = '';
        contentFile = null;
        contentPreviewContainer.style.display = 'none';
        contentInput.closest('.upload-area').querySelector('.upload-instructions').style.display = 'block';
        updateUploadButtonState();
    });

    removeStyleBtn.addEventListener('click', () => {
        styleInput.value = '';
        styleFile = null;
        stylePreviewContainer.style.display = 'none';
        styleInput.closest('.upload-area').querySelector('.upload-instructions').style.display = 'block';
        updateUploadButtonState();
    });

    // Slider value display
    const sliders = document.querySelectorAll('.slider-container input[type="range"]');
    sliders.forEach(slider => {
        const display = document.getElementById(`${slider.id}-display`);
        display.textContent = slider.value;
        slider.addEventListener('input', () => {
            display.textContent = parseFloat(slider.value).toFixed(slider.step.includes('.') ? 3 : 0);
        });
    });

    // Preset buttons
    const presetButtons = document.querySelectorAll('.preset-btn');
    const presetConfigs = {
        balanced: {
            'content-weight': 1.0,
            'style-weight': 1.0,
            'steps': 300,
            'learning-rate': 0.003,
            'conv1-1-weight': 1.0,
            'conv2-1-weight': 0.8,
            'conv3-1-weight': 0.5,
            'conv4-1-weight': 0.3,
            'conv5-1-weight': 0.1
        },
        'content-focused': {
            'content-weight': 5.0,
            'style-weight': 0.5,
            'steps': 300,
            'learning-rate': 0.003,
            'conv1-1-weight': 1.0,
            'conv2-1-weight': 0.8,
            'conv3-1-weight': 0.5,
            'conv4-1-weight': 0.3,
            'conv5-1-weight': 0.1
        },
        'style-focused': {
            'content-weight': 0.5,
            'style-weight': 5.0,
            'steps': 400,
            'learning-rate': 0.003,
            'conv1-1-weight': 1.0,
            'conv2-1-weight': 0.8,
            'conv3-1-weight': 0.5,
            'conv4-1-weight': 0.3,
            'conv5-1-weight': 0.1
        },
        'fine-details': {
            'content-weight': 1.0,
            'style-weight': 1.0,
            'steps': 300,
            'learning-rate': 0.003,
            'conv1-1-weight': 1.5,
            'conv2-1-weight': 1.2,
            'conv3-1-weight': 0.8,
            'conv4-1-weight': 0.5,
            'conv5-1-weight': 0.3
        },
        'large-patterns': {
            'content-weight': 1.0,
            'style-weight': 1.0,
            'steps': 300,
            'learning-rate': 0.003,
            'conv1-1-weight': 0.5,
            'conv2-1-weight': 0.7,
            'conv3-1-weight': 1.0,
            'conv4-1-weight': 1.2,
            'conv5-1-weight': 1.5
        }
    };

    presetButtons.forEach(button => {
        button.addEventListener('click', () => {
            presetButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const preset = presetConfigs[button.dataset.preset];
            Object.keys(preset).forEach(key => {
                const slider = document.getElementById(key);
                const display = document.getElementById(`${key}-display`);
                slider.value = preset[key];
                display.textContent = parseFloat(preset[key]).toFixed(slider.step.includes('.') ? 3 : 0);
            });
        });
    });

    // Toast notifications
    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>${message}`;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // Upload images
    uploadBtn.addEventListener('click', async () => {
        uploadBtn.disabled = true;
        const formData = new FormData();
        formData.append('content_image', contentFile);
        formData.append('style_image', styleFile);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                contentId = data.content_id;
                styleId = data.style_id;
                document.getElementById('parameters-section').classList.remove('hidden');
                document.getElementById('upload-container').scrollIntoView({ behavior: 'smooth' });
                showToast('Images uploaded successfully!');
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Error uploading images', 'error');
        } finally {
            uploadBtn.disabled = false;
        }
    });

    // Start style transfer
    const startTransferBtn = document.getElementById('start-transfer-btn');
    startTransferBtn.addEventListener('click', async () => {
        startTransferBtn.disabled = true;
        document.getElementById('results-section').classList.remove('hidden');
        document.getElementById('processing-indicator').style.display = 'block';
        document.getElementById('result-container').style.display = 'none';
        document.getElementById('parameters-section').scrollIntoView({ behavior: 'smooth' });

        const formData = new FormData();
        formData.append('content_id', contentId);
        formData.append('style_id', styleId);
        formData.append('content_weight', document.getElementById('content-weight').value);
        formData.append('style_weight', document.getElementById('style-weight').value * 1e6);
        formData.append('steps', document.getElementById('steps').value);
        formData.append('learning_rate', document.getElementById('learning-rate').value);
        formData.append('conv1_1_weight', document.getElementById('conv1-1-weight').value);
        formData.append('conv2_1_weight', document.getElementById('conv2-1-weight').value);
        formData.append('conv3_1_weight', document.getElementById('conv3-1-weight').value);
        formData.append('conv4_1_weight', document.getElementById('conv4-1-weight').value);
        formData.append('conv5_1_weight', document.getElementById('conv5-1-weight').value);

        try {
            const response = await fetch('/transfer', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                // Update progress
                const steps = parseInt(document.getElementById('steps').value);
                const progressBar = document.getElementById('progress-bar');
                const progressText = document.getElementById('progress-text');
                data.progress.forEach((step, index) => {
                    setTimeout(() => {
                        const percentage = (step.step / steps) * 100;
                        progressBar.style.width = `${percentage}%`;
                        progressText.textContent = `Step: ${step.step}/${steps}`;
                        if (index === data.progress.length - 1) {
                            // Show results
                            document.getElementById('processing-indicator').style.display = 'none';
                            document.getElementById('result-container').style.display = 'block';
                            document.getElementById('content-result').src = contentPreview.src;
                            document.getElementById('style-result').src = stylePreview.src;
                            document.getElementById('stylized-result').src = data.preview;
                            document.getElementById('download-btn').href = `/download/${data.result_id}`;
                            showToast('Style transfer completed!');
                        }
                    }, 1000 * index);
                });
            } else {
                showToast(data.message, 'error');
                document.getElementById('processing-indicator').style.display = 'none';
            }
        } catch (error) {
            showToast('Error performing style transfer', 'error');
            document.getElementById('processing-indicator').style.display = 'none';
        } finally {
            startTransferBtn.disabled = false;
        }
    });

    // Retry with different parameters
    document.getElementById('retry-btn').addEventListener('click', () => {
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('parameters-section').scrollIntoView({ behavior: 'smooth' });
    });

    // Try new images
    document.getElementById('new-images-btn').addEventListener('click', () => {
        contentInput.value = '';
        styleInput.value = '';
        contentFile = null;
        styleFile = null;
        contentPreviewContainer.style.display = 'none';
        stylePreviewContainer.style.display = 'none';
        contentInput.closest('.upload-area').querySelector('.upload-instructions').style.display = 'block';
        styleInput.closest('.upload-area').querySelector('.upload-instructions').style.display = 'block';
        document.getElementById('parameters-section').classList.add('hidden');
        document.getElementById('results-section').classList.add('hidden');
        updateUploadButtonState();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Health check
    fetch('/health')
        .then(response => response.json())
        .then(data => {
            if (data.api_status !== 'Online') {
                showToast('API is offline. Some features may not work.', 'error');
            }
        })
        .catch(() => {
            showToast('Unable to connect to API', 'error');
        });
});