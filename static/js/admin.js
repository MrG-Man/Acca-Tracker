// Football Predictions Admin Interface JavaScript

class AdminInterface {
    constructor() {
        this.overrideModal = null;
        this.selectedReason = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateAllDropdowns();
    }

    setupEventListeners() {
        // Assignment buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('assign-btn')) {
                this.handleAssignment(e.target);
            }

            if (e.target.classList.contains('unassign-btn')) {
                this.handleUnassignment(e.target);
            }

            if (e.target.id === 'override-btn') {
                this.showOverrideModal();
            }

            if (e.target.classList.contains('modal-close') || e.target.classList.contains('modal-cancel')) {
                this.hideOverrideModal();
            }

            if (e.target.id === 'confirm-override-btn') {
                this.handleOverrideConfirmation();
            }
        });

        // Dropdown changes - use input event for better responsiveness
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('selector-dropdown')) {
                this.handleDropdownChange(e.target);
            }
        });

        // Also listen for focus events to ensure dropdowns are properly initialized
        document.addEventListener('focusin', (e) => {
            if (e.target.classList.contains('selector-dropdown')) {
                // Reset status display when dropdown gets focus
                const matchCard = e.target.closest('.match-card');
                const statusDiv = matchCard.querySelector('.assignment-status');
                if (statusDiv) {
                    statusDiv.style.display = 'none';
                }
            }
        });

        // Radio button changes for override reason
        document.addEventListener('change', (e) => {
            if (e.target.name === 'override-reason') {
                this.selectedReason = e.target.value;
            }
        });

        // Modal backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.id === 'override-modal') {
                this.hideOverrideModal();
            }
        });
    }

    async handleAssignment(button) {
        // This method is kept for backward compatibility
        // The new implementation triggers assignment directly on dropdown change
        const matchCard = button.closest('.match-card');
        const dropdown = matchCard.querySelector('.selector-dropdown');

        if (dropdown && dropdown.value) {
            // Trigger the dropdown change handler which now handles the assignment
            this.handleDropdownChange(dropdown);
        } else {
            this.showMessage('Please select a selector first', 'error');
        }
    }

    async handleUnassignment(button) {
        const selector = button.dataset.selector;

        if (!confirm(`Are you sure you want to unassign the match from ${selector}?`)) {
            return;
        }

        try {
            const response = await fetch('/api/unassign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    selector: selector
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showMessage(result.message, 'success');
                this.updateSummaryPanel();
                this.refreshPage();
            } else {
                this.showMessage(result.error, 'error');
            }
        } catch (error) {
            this.showMessage('Network error occurred', 'error');
            console.error('Unassignment error:', error);
        }
    }

    async handleDropdownChange(dropdown) {
        const matchCard = dropdown.closest('.match-card');
        const statusDiv = matchCard.querySelector('.assignment-status');
        const statusText = statusDiv.querySelector('.status-text');
        const statusSpinner = statusDiv.querySelector('.status-spinner');
        const selector = dropdown.value;

        if (!selector) {
            // Reset status if no selector selected
            statusDiv.style.display = 'none';
            return;
        }

        // Show loading state
        statusDiv.style.display = 'flex';
        statusText.textContent = `Assigning to ${selector}...`;
        statusSpinner.style.display = 'inline-block';

        try {
            // Get match ID from the dropdown's data attribute
            const matchId = dropdown.dataset.matchId;

            // Make the assignment API call
            const response = await fetch('/api/assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    match_id: matchId,
                    selector: selector
                })
            });

            const result = await response.json();

            if (result.success) {
                // Show success state briefly
                statusText.textContent = `✓ Assigned to ${selector}`;
                statusSpinner.style.display = 'none';
                statusText.style.color = '#4caf50';

                // Refresh the page after a short delay to show the success message
                setTimeout(() => {
                    this.refreshPage();
                }, 1000);
            } else {
                // Show error state
                statusText.textContent = `✗ ${result.error}`;
                statusSpinner.style.display = 'none';
                statusText.style.color = '#f44336';

                // Reset dropdown after error
                setTimeout(() => {
                    dropdown.value = '';
                    statusDiv.style.display = 'none';
                }, 2000);
            }
        } catch (error) {
            // Show error state
            statusText.textContent = '✗ Network error';
            statusSpinner.style.display = 'none';
            statusText.style.color = '#f44336';
            console.error('Assignment error:', error);

            // Reset dropdown after error
            setTimeout(() => {
                dropdown.value = '';
                statusDiv.style.display = 'none';
            }, 2000);
        }
    }

    updateAllDropdowns() {
        // Reset all assignment status displays
        const statusDivs = document.querySelectorAll('.assignment-status');
        statusDivs.forEach(statusDiv => {
            statusDiv.style.display = 'none';
        });
    }

    showOverrideModal() {
        const modal = document.getElementById('override-modal');
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';

            // Reset form
            const confirmInput = document.getElementById('override-confirm');
            if (confirmInput) confirmInput.value = '';

            const confirmBtn = document.getElementById('confirm-override-btn');
            if (confirmBtn) confirmBtn.disabled = true;

            this.selectedReason = null;
        }
    }

    hideOverrideModal() {
        const modal = document.getElementById('override-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }

    validateOverrideForm() {
        const confirmInput = document.getElementById('override-confirm');
        const confirmBtn = document.getElementById('confirm-override-btn');

        const requiredText = "I confirm that I want to proceed with fewer than 8 selections";
        const isTextValid = confirmInput && confirmInput.value === requiredText;
        const isReasonSelected = this.selectedReason !== null;

        if (confirmBtn) {
            confirmBtn.disabled = !(isTextValid && isReasonSelected);
        }

        return isTextValid && isReasonSelected;
    }

    async handleOverrideConfirmation() {
        if (!this.validateOverrideForm()) {
            this.showMessage('Please complete all confirmation requirements', 'error');
            return;
        }

        try {
            const response = await fetch('/api/override', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    confirm_message: "I confirm that I want to proceed with fewer than 8 selections",
                    reason: this.selectedReason
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showMessage('Override confirmed successfully', 'success');
                this.hideOverrideModal();
                this.refreshPage();
            } else {
                this.showMessage(result.error, 'error');
            }
        } catch (error) {
            this.showMessage('Network error occurred', 'error');
            console.error('Override error:', error);
        }
    }

    showMessage(message, type) {
        // Create and show a temporary message
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;

        // Style the message
        Object.assign(messageDiv.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '1rem 1.5rem',
            borderRadius: '6px',
            color: 'white',
            fontWeight: '500',
            zIndex: '9999',
            opacity: '0',
            transform: 'translateY(-20px)',
            transition: 'all 0.3s ease'
        });

        if (type === 'success') {
            messageDiv.style.backgroundColor = '#4caf50';
        } else {
            messageDiv.style.backgroundColor = '#f44336';
        }

        document.body.appendChild(messageDiv);

        // Animate in
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 10);

        // Remove after 3 seconds
        setTimeout(() => {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 300);
        }, 3000);
    }

    refreshPage() {
        // Refresh the page to show updated data
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    updateSummaryPanel() {
        // Update the summary panel counts and progress
        const assignedSelectors = document.querySelectorAll('.selector-badge.assigned').length;
        const totalSelectors = document.querySelectorAll('.selector-badge').length;
        const availableSelectors = totalSelectors - assignedSelectors;

        // Update counts in the progress indicator
        const assignedCountEl = document.querySelector('.assigned-count');
        const totalCountEl = document.querySelector('.total-count');
        const availableCountEl = document.querySelector('.status-column h3');
        const progressTextEl = document.querySelector('.progress-text');

        if (assignedCountEl) assignedCountEl.textContent = assignedSelectors;
        if (totalCountEl) totalCountEl.textContent = totalSelectors;

        // Update available selectors count in header
        if (availableCountEl && availableCountEl.textContent.includes('Available Selectors')) {
            availableCountEl.textContent = `Available Selectors (${availableSelectors})`;
        }

        // Update the next available/assigned header
        const assignedHeader = document.querySelector('.status-column:nth-child(2) h3');
        if (assignedHeader && assignedHeader.textContent.includes('Assigned Selectors')) {
            assignedHeader.textContent = `Assigned Selectors (${assignedSelectors})`;
        }

        // Update progress percentage
        const progressPercentage = totalSelectors > 0 ? Math.round((assignedSelectors / totalSelectors) * 100) : 0;
        if (progressTextEl) progressTextEl.textContent = `${progressPercentage}% Complete`;

        // Update progress bar width
        const progressFill = document.querySelector('.progress-fill');
        if (progressFill) {
            progressFill.style.width = `${progressPercentage}%`;
        }

        // Update "Still Need" stat if it exists
        const stillNeedStat = document.querySelector('.stat-item.warning .stat-value');
        if (stillNeedStat) {
            const needed = 8 - assignedSelectors;
            stillNeedStat.textContent = `${needed} more selection${needed !== 1 ? 's' : ''}`;
        }
    }

    async refreshSummaryData() {
        // Fetch current data and update the summary panel
        try {
            const response = await fetch('/api/selections');
            const data = await response.json();

            if (data.success) {
                this.updateSummaryPanelWithData(data.selections, data.all_selectors);
            }
        } catch (error) {
            console.error('Error refreshing summary data:', error);
        }
    }

    updateSummaryPanelWithData(selections, allSelectors) {
        // This would be used if we want to completely rebuild the summary panel
        // For now, we'll use the incremental update approach above
        console.log('Summary data refreshed:', { selections: selections.length, total: allSelectors.length });
    }

    // Update confirmation button state when form changes
    updateOverrideButtonState() {
        const confirmInput = document.getElementById('override-confirm');
        if (confirmInput) {
            confirmInput.addEventListener('input', () => {
                this.validateOverrideForm();
            });
        }
    }
}

// Initialize the admin interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const admin = new AdminInterface();

    // Update override button state
    admin.updateOverrideButtonState();

    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // ESC key to close modal
        if (e.key === 'Escape') {
            admin.hideOverrideModal();
        }
    });
});

// Utility functions for future enhancements
const AdminUtils = {
    // Format date for display
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    // Debounce function for search inputs (future enhancement)
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Local storage helpers for preferences (future enhancement)
    savePreference: (key, value) => {
        try {
            localStorage.setItem(`admin_pref_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn('Could not save preference:', e);
        }
    },

    getPreference: (key, defaultValue = null) => {
        try {
            const item = localStorage.getItem(`admin_pref_${key}`);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.warn('Could not get preference:', e);
            return defaultValue;
        }
    }
};