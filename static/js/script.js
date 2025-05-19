document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('zipfile');
    const uploadArea = document.querySelector('.upload-area');
    const browseBtn = document.getElementById('browse-btn');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const removeFileBtn = document.getElementById('remove-file');
    const extractBtn = document.getElementById('extract-btn');

    // Click on the upload area to trigger file input
    if (uploadArea) {
        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });
    }

    // Click on the browse button to trigger file input
    if (browseBtn) {
        browseBtn.addEventListener('click', function() {
            fileInput.click();
        });
    }

    // Handle file selection
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            handleFileSelection(this.files);
        });
    }

    // Remove selected file
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', function() {
            fileInput.value = '';
            fileInfo.classList.add('d-none');
            extractBtn.disabled = true;
        });
    }

    // Handle drag and drop
    if (uploadArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });

        uploadArea.addEventListener('drop', handleDrop, false);
    }

    // Prevent default behaviors
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight the upload area when dragging over
    function highlight() {
        uploadArea.classList.add('drag-over');
    }

    // Remove highlight
    function unhighlight() {
        uploadArea.classList.remove('drag-over');
    }

    // Handle file drop
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFileSelection(files);
    }

    // Handle file selection (from input or drop)
    function handleFileSelection(files) {
        if (files.length > 0) {
            const file = files[0];
            
            // Check if it's a zip file
            if (file.type === 'application/zip' || file.name.toLowerCase().endsWith('.zip')) {
                // Show file info
                fileName.textContent = file.name;
                fileSize.textContent = formatFileSize(file.size);
                fileInfo.classList.remove('d-none');
                extractBtn.disabled = false;
            } else {
                alert('Please select a valid ZIP file.');
                fileInput.value = '';
            }
        }
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Show loading spinner when form is submitted
    if (form) {
        form.addEventListener('submit', function() {
            // Validate that a file is selected
            if (fileInput.files.length === 0) {
                alert('Please select a ZIP file.');
                return false;
            }
            
            // Disable the extract button and show loading state
            extractBtn.disabled = true;
            extractBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Extracting...';
            
            return true;
        });
    }
});
