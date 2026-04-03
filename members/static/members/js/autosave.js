/**
 * Auto-save functionality for DIY application forms
 */
class AutoSave {
    constructor(options = {}) {
        // Default options
        this.options = {
            formSelector: 'form.autosave-form',
            saveEndpoint: '/diy/api/autosave/',
            debounceDelay: 1000,
            autoSaveInterval: 10000,
            showSaveStatus: true,
            saveStatusSelector: '.autosave-status',
            saveStatusDuration: 3000,
            maxRetries: 3,
            useModal: true,
            ...options
        };

        // State variables
        this.form = document.querySelector(this.options.formSelector);
        this.saveStatusElement = document.querySelector(this.options.saveStatusSelector);
        this.lastSavedData = null;
        this.changesPending = false;
        this.saveInProgress = false;
        this.retryCount = 0;
        this.stepNumber = this.getStepNumber();
        this.debounceTimer = null;
        this.intervalTimer = null;
        this.csrfToken = this.getCsrfToken();
        this.applicationToken = null;

        // Initialize if form exists
        if (this.form) {
            this.init();
        } else {
            console.error('AutoSave: Form not found');
        }
    }

    /**
     * Initialize auto-save functionality
     */
    init() {
        // Add event listeners to form inputs
        this.form.querySelectorAll('input, select, textarea').forEach(element => {
            element.addEventListener('change', () => this.handleFormChange());
            element.addEventListener('input', () => this.handleFormChange());
        });

        // Start periodic auto-save interval
        this.intervalTimer = setInterval(() => this.checkForChanges(), this.options.autoSaveInterval);

        // Check for existing incomplete applications
        this.checkForIncompleteApplication();

        // Initial save of form data
        this.saveFormData();

        // Add event listener for save-for-later button
        const saveForLaterBtn = document.querySelector('.save-for-later-btn');
        if (saveForLaterBtn) {
            saveForLaterBtn.addEventListener('click', () => this.handleSaveForLater());
        }

        console.log('AutoSave initialized for step', this.stepNumber);
    }

    /**
     * Handle form input changes
     */
    handleFormChange() {
        this.changesPending = true;
        
        // Clear existing timer and set a new one
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        this.debounceTimer = setTimeout(() => {
            this.saveFormData();
        }, this.options.debounceDelay);
    }

    /**
     * Check if there are pending changes and save if needed
     */
    checkForChanges() {
        if (this.changesPending && !this.saveInProgress) {
            this.saveFormData();
        }
    }

    /**
     * Get the current step number from the form data attribute or URL
     */
    getStepNumber() {
        // Try to get step from form data attribute
        if (this.form && this.form.dataset.step) {
            return parseInt(this.form.dataset.step);
        }
        
        // Try to get step from URL
        const urlMatch = window.location.pathname.match(/\/step\/(\d+)/);
        if (urlMatch && urlMatch[1]) {
            return parseInt(urlMatch[1]);
        }
        
        // Default to 1 if not found
        return 1;
    }

    /**
     * Get CSRF token from cookie
     */
    getCsrfToken() {
        const name = 'csrftoken';
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }

    /**
     * Collect form data and save it
     */
    saveFormData() {
        if (this.saveInProgress) {
            return;
        }
        
        this.saveInProgress = true;
        this.updateSaveStatus('saving');
        
        // Trigger autosave:start event for modal
        if (this.options.useModal) {
            window.dispatchEvent(new CustomEvent('autosave:start'));
        }
        
        // Collect form data
        const formData = {};
        const formElements = this.form.elements;
        
        for (let i = 0; i < formElements.length; i++) {
            const element = formElements[i];
            
            // Skip buttons, submit inputs, and elements without names
            if (!element.name || element.type === 'button' || element.type === 'submit') {
                continue;
            }
            
            // Handle different input types
            if (element.type === 'checkbox') {
                formData[element.name] = element.checked;
            } else if (element.type === 'radio') {
                if (element.checked) {
                    formData[element.name] = element.value;
                }
            } else if (element.type === 'select-multiple') {
                const selectedValues = [];
                for (let j = 0; j < element.options.length; j++) {
                    if (element.options[j].selected) {
                        selectedValues.push(element.options[j].value);
                    }
                }
                formData[element.name] = selectedValues;
            } else {
                formData[element.name] = element.value;
            }
        }
        
        // Check if data has changed
        const currentDataString = JSON.stringify(formData);
        if (currentDataString === this.lastSavedData) {
            this.saveInProgress = false;
            this.changesPending = false;
            return;
        }
        
        // Prepare data for API
        const payload = {
            step: this.stepNumber,
            form_data: formData
        };
        
        // Send data to server
        fetch(this.options.saveEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(payload),
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                this.lastSavedData = currentDataString;
                this.changesPending = false;
                this.retryCount = 0;
                this.applicationToken = data.token || null;
                this.updateSaveStatus('saved', data.timestamp);
                
                // Trigger autosave:success event for modal
                if (this.options.useModal) {
                    window.dispatchEvent(new CustomEvent('autosave:success', {
                        detail: {
                            token: this.applicationToken,
                            timestamp: data.timestamp,
                            step: this.stepNumber
                        }
                    }));
                }
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('AutoSave error:', error);
            this.updateSaveStatus('error');
            
            // Trigger autosave:error event for modal
            if (this.options.useModal) {
                window.dispatchEvent(new CustomEvent('autosave:error', {
                    detail: {
                        message: error.message || 'Failed to save application data.'
                    }
                }));
            }
            
            // Retry logic
            if (this.retryCount < this.options.maxRetries) {
                this.retryCount++;
                setTimeout(() => {
                    this.saveInProgress = false;
                    this.saveFormData();
                }, 2000 * this.retryCount); // Exponential backoff
            } else {
                this.changesPending = true; // Keep changes pending for next interval
            }
        })
        .finally(() => {
            this.saveInProgress = false;
        });
    }

    /**
     * Update save status indicator
     */
    updateSaveStatus(status, timestamp = null) {
        if (!this.options.showSaveStatus || !this.saveStatusElement) {
            return;
        }
        
        let message = '';
        let className = '';
        
        switch (status) {
            case 'saving':
                message = 'Saving...';
                className = 'autosave-saving';
                break;
            case 'saved':
                const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
                message = `Last saved at ${time}`;
                className = 'autosave-saved';
                break;
            case 'error':
                message = 'Failed to save. Retrying...';
                className = 'autosave-error';
                break;
        }
        
        this.saveStatusElement.textContent = message;
        this.saveStatusElement.className = this.options.saveStatusSelector.replace('.', '') + ' ' + className;
        
        // Hide success message after a delay
        if (status === 'saved') {
            setTimeout(() => {
                if (this.saveStatusElement.classList.contains('autosave-saved')) {
                    this.saveStatusElement.classList.add('autosave-fade');
                }
            }, this.options.saveStatusDuration);
        }
    }
    
    /**
     * Check for existing incomplete application
     */
    checkForIncompleteApplication() {
        // Get the application token from URL or localStorage
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get('token');
        const tokenFromStorage = localStorage.getItem('autosave_application_token');
        
        const token = tokenFromUrl || tokenFromStorage;
        
        if (!token) {
            return;
        }
        
        // Check if there's an incomplete application with this token
        fetch(`/members/api/diy/check-application/${token}/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.exists) {
                // Store the token
                this.applicationToken = token;
                localStorage.setItem('autosave_application_token', token);
                
                // Format the last updated time
                const lastUpdated = new Date(data.last_updated);
                const formattedDate = lastUpdated.toLocaleDateString();
                const formattedTime = lastUpdated.toLocaleTimeString();
                const hoursSince = data.hours_since_update;
                
                // Trigger the resume modal
                window.dispatchEvent(new CustomEvent('autosave:resume', {
                    detail: {
                        token: token,
                        lastSaved: data.last_updated,
                        formattedDate: formattedDate,
                        formattedTime: formattedTime,
                        hoursSince: hoursSince,
                        currentStep: data.current_step,
                        resumeUrl: data.resume_url
                    }
                }));
            }
        })
        .catch(error => {
            console.error('Error checking for incomplete application:', error);
        });
    }

    /**
     * Handle Save for Later button click
     */
    handleSaveForLater() {
        // Force an immediate save
        this.saveFormData();
        
        // If save is in progress, wait a bit before showing the modal
        if (this.saveInProgress) {
            setTimeout(() => this.showSaveForLaterModal(), 1000);
        } else {
            this.showSaveForLaterModal();
        }
    }
    
    /**
     * Show the Save for Later modal with application token and resume link
     */
    showSaveForLaterModal() {
        // Show a modal with the application token
        if (this.options.useModal && this.applicationToken) {
            // Store token in localStorage for future reference
            localStorage.setItem('autosave_application_token', this.applicationToken);
            
            // Create a shareable link for the user
            const shareableLink = `${window.location.origin}/members/diy/resume/${this.applicationToken}/`;
            console.log('Shareable link:', shareableLink);
            
            // Dispatch event to show modal
            window.dispatchEvent(new CustomEvent('autosave:success', {
                detail: {
                    token: this.applicationToken,
                    timestamp: new Date().toISOString(),
                    step: this.stepNumber,
                    saveForLater: true,
                    resumeUrl: shareableLink
                }
            }));
            
            // Copy to clipboard if supported
            if (navigator.clipboard) {
                navigator.clipboard.writeText(shareableLink)
                    .then(() => console.log('Link copied to clipboard'))
                    .catch(err => console.error('Failed to copy link:', err));
            }
        } else {
            alert('Your application has been saved. You can resume it later.');
        }
    }
    
    /**
     * Clean up event listeners and timers
     */
    destroy() {
        if (this.intervalTimer) {
            clearInterval(this.intervalTimer);
        }
        
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        if (this.form) {
            this.form.querySelectorAll('input, select, textarea').forEach(element => {
                element.removeEventListener('change', this.handleFormChange);
                element.removeEventListener('input', this.handleFormChange);
            });
        }
    }
}

// Initialize auto-save when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.autoSave = new AutoSave();
});
