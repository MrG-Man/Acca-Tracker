// Football Predictions Admin Interface JavaScript
// Enhanced with improved error handling, logging, and debugging

class AdminInterface {
    constructor() {
        this.overrideModal = null;
        this.selectedReason = null;
        this.requestQueue = new Map(); // Track ongoing requests to prevent race conditions
        this.debugMode = localStorage.getItem('admin_debug_mode') === 'true';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateAllDropdowns();
        this.setupSearchFunctionality();
        this.logDebug('AdminInterface initialized');

        // Add mobile detection and logging
        this.logMobileInfo();
        this.logElementVisibility();
    }

    logDebug(message, data = null) {
        const isMobile = window.innerWidth <= 768;
        if (this.debugMode || isMobile) {
            const timestamp = new Date().toISOString();
            console.log(`[ADMIN_DEBUG ${timestamp}] ${message}`, data || '');
        }
    }

    logError(message, error = null) {
        const timestamp = new Date().toISOString();
        console.error(`[ADMIN_ERROR ${timestamp}] ${message}`, error || '');
        this.logDebug('Error occurred', { message, error: error?.stack || error });
    }

    logMobileInfo() {
        const isMobile = window.innerWidth <= 768;
        const screenInfo = {
            width: window.innerWidth,
            height: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio,
            userAgent: navigator.userAgent
        };
        this.logDebug('Screen and device info', screenInfo);
        if (isMobile) {
            this.logDebug('Mobile device detected - potential visibility issues may occur');
        }
    }

    logElementVisibility() {
        const assignedSelectors = document.querySelectorAll('.selector-item.assigned');
        const assignedBadges = document.querySelectorAll('.assigned-badge');
        const matchesGrid = document.querySelector('.matches-grid');
        const selectorSummary = document.querySelector('.selector-summary-panel');

        const visibilityInfo = {
            assignedSelectorsCount: assignedSelectors.length,
            assignedBadgesCount: assignedBadges.length,
            matchesGridChildren: matchesGrid ? matchesGrid.children.length : 0,
            selectorSummaryVisible: selectorSummary ? getComputedStyle(selectorSummary).display !== 'none' : false
        };

        this.logDebug('Element visibility check', visibilityInfo);

        // Log styles for assigned elements
        assignedSelectors.forEach((el, index) => {
            const style = getComputedStyle(el);
            this.logDebug(`Assigned selector ${index} styles`, {
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                height: style.height,
                width: style.width
            });
        });
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

        // Team search functionality
        const teamSearchInput = document.getElementById('team-search');
        const clearSearchBtn = document.getElementById('clear-search');

        if (teamSearchInput) {
            teamSearchInput.addEventListener('input', (e) => {
                this.handleTeamSearch(e.target.value);
                this.toggleClearButton(e.target.value);
            });

            teamSearchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.clearTeamSearch();
                }
            });
        }

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                this.clearTeamSearch();
            });
        }
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

        console.log('[ADMIN_DEBUG] handleDropdownChange called:', { selector, matchId: dropdown.dataset.matchId });

        if (!selector) {
            // Reset status if no selector selected
            statusDiv.style.display = 'none';
            return;
        }

        // Get match ID from the dropdown's data attribute
        const matchId = dropdown.dataset.matchId;
        const requestKey = `${matchId}_${selector}`;

        // Prevent race conditions by checking if request is already in progress
        if (this.requestQueue.has(requestKey)) {
            this.logDebug(`Request already in progress for ${requestKey}, ignoring duplicate`);
            return;
        }

        // Add to request queue
        this.requestQueue.set(requestKey, { dropdown, matchCard, statusDiv, statusText, statusSpinner });
        this.logDebug(`Added request to queue: ${requestKey}`);

        // Show loading state
        statusDiv.style.display = 'flex';
        statusText.textContent = `Assigning to ${selector}...`;
        statusSpinner.style.display = 'inline-block';

        try {
            await this.performAssignmentWithRetry(dropdown, matchId, selector, requestKey);
        } catch (error) {
            this.handleAssignmentError(dropdown, statusDiv, statusText, statusSpinner, error, requestKey);
        } finally {
            // Remove from request queue
            this.requestQueue.delete(requestKey);
            this.logDebug(`Removed request from queue: ${requestKey}`);
        }
    }

    async performAssignmentWithRetry(dropdown, matchId, selector, requestKey, maxRetries = 3) {
        let lastError;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                this.logDebug(`Assignment attempt ${attempt}/${maxRetries} for ${requestKey}`);

                // Make the assignment API call with cache-busting
                const response = await fetch(`/api/assign?_t=${Date.now()}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    },
                    body: JSON.stringify({
                        match_id: matchId,
                        selector: selector,
                        timestamp: Date.now(),
                        attempt: attempt
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();

                if (result.success) {
                    this.handleAssignmentSuccess(dropdown, selector, requestKey);
                    return; // Success, exit retry loop
                } else {
                    // Server returned error
                    throw new Error(result.error || 'Unknown server error');
                }

            } catch (error) {
                lastError = error;
                this.logError(`Assignment attempt ${attempt} failed for ${requestKey}`, error);

                // If this isn't the last attempt, wait before retrying
                if (attempt < maxRetries) {
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000); // Exponential backoff, max 5s
                    this.logDebug(`Waiting ${delay}ms before retry ${attempt + 1}`);
                    await this.delay(delay);
                }
            }
        }

        // All retries failed
        throw lastError;
    }

    handleAssignmentSuccess(dropdown, selector, requestKey) {
        // Update UI for all queued requests for this dropdown
        this.requestQueue.forEach((requestData, key) => {
            if (key.startsWith(requestKey.split('_')[0])) {
                const { statusDiv, statusText, statusSpinner } = requestData;
                statusText.textContent = `✓ Assigned to ${selector}`;
                statusSpinner.style.display = 'none';
                statusText.style.color = '#4caf50';
            }
        });

        this.logDebug(`Assignment successful for ${requestKey}`);

        // Refresh the page after a short delay to show the success message
        setTimeout(() => {
            this.refreshPage();
        }, 1000);
    }

    handleAssignmentError(dropdown, statusDiv, statusText, statusSpinner, error, requestKey) {
        const errorMessage = this.getDetailedErrorMessage(error);

        // Update UI for all queued requests for this dropdown
        this.requestQueue.forEach((requestData, key) => {
            if (key.startsWith(requestKey.split('_')[0])) {
                const { statusText: reqStatusText, statusSpinner: reqStatusSpinner } = requestData;
                reqStatusText.textContent = `✗ ${errorMessage}`;
                reqStatusSpinner.style.display = 'none';
                reqStatusText.style.color = '#f44336';
            }
        });

        this.logError(`Assignment failed for ${requestKey}`, error);

        // Reset dropdown after error
        setTimeout(() => {
            dropdown.value = '';
            statusDiv.style.display = 'none';

            // Clear any remaining requests for this dropdown
            this.requestQueue.forEach((_, key) => {
                if (key.startsWith(requestKey.split('_')[0])) {
                    this.requestQueue.delete(key);
                }
            });
        }, 3000);
    }

    getDetailedErrorMessage(error) {
        if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
            return 'Network error - please check connection';
        } else if (error.message.includes('HTTP 5')) {
            return 'Server error - please try again later';
        } else if (error.message.includes('HTTP 4')) {
            return 'Request error - please check your input';
        } else if (error.message.includes('timeout')) {
            return 'Request timeout - please try again';
        } else {
            return 'Assignment failed - please try again';
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    updateAllDropdowns() {
        // Reset all assignment status displays
        const statusDivs = document.querySelectorAll('.assignment-status');
        this.logDebug('Updating all dropdowns', { statusDivsCount: statusDivs.length });
        statusDivs.forEach(statusDiv => {
            statusDiv.style.display = 'none';
        });
        this.logElementVisibility(); // Re-check visibility after update
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

    showMessage(message, type, options = {}) {
        const {
            duration = 3000,
            persistent = false,
            debugInfo = null,
            actionButton = null
        } = options;

        // Create and show a temporary message
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;

        // Add debug information if available
        let displayMessage = message;
        if (debugInfo && this.debugMode) {
            displayMessage += `\n[Debug: ${debugInfo}]`;
        }

        messageDiv.textContent = displayMessage;

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
            transition: 'all 0.3s ease',
            maxWidth: '400px',
            wordWrap: 'break-word',
            whiteSpace: 'pre-line'
        });

        if (type === 'success') {
            messageDiv.style.backgroundColor = '#4caf50';
        } else if (type === 'warning') {
            messageDiv.style.backgroundColor = '#ff9800';
        } else {
            messageDiv.style.backgroundColor = '#f44336';
        }

        // Add action button if provided
        if (actionButton) {
            const button = document.createElement('button');
            button.textContent = actionButton.text;
            button.className = 'message-action-btn';
            button.onclick = actionButton.onClick;
            Object.assign(button.style, {
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                color: 'white',
                padding: '0.25rem 0.5rem',
                marginTop: '0.5rem',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '0.8em'
            });
            messageDiv.appendChild(document.createElement('br'));
            messageDiv.appendChild(button);
        }

        document.body.appendChild(messageDiv);

        // Animate in
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 10);

        // Auto-remove after duration (unless persistent)
        if (!persistent) {
            setTimeout(() => {
                messageDiv.style.opacity = '0';
                messageDiv.style.transform = 'translateY(-20px)';
                setTimeout(() => {
                    if (messageDiv.parentNode) {
                        messageDiv.parentNode.removeChild(messageDiv);
                    }
                }, 300);
            }, duration);
        }

        // Store reference for potential manual removal
        messageDiv.remove = () => {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 300);
        };

        return messageDiv;
    }

    validateFormData(data) {
        const errors = [];

        if (!data.match_id || typeof data.match_id !== 'string') {
            errors.push('Invalid match ID');
        }

        if (!data.selector || typeof data.selector !== 'string') {
            errors.push('Invalid selector');
        }

        if (data.selector && !this.isValidSelector(data.selector)) {
            errors.push(`Invalid selector: ${data.selector}`);
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    isValidSelector(selector) {
        // This should match the SELECTORS array from the backend
        const validSelectors = [
            "Glynny", "Eamonn Bone", "Mickey D", "Rob Carney",
            "Steve H", "Danny", "Eddie Lee", "Fran Radar"
        ];
        return validSelectors.includes(selector);
    }

    showDebugPanel() {
        if (!this.debugMode) return;

        // Create debug panel
        const debugPanel = document.createElement('div');
        debugPanel.id = 'admin-debug-panel';
        debugPanel.innerHTML = `
            <div style="position: fixed; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); color: white; padding: 1rem; border-radius: 5px; font-family: monospace; font-size: 0.8em; max-width: 300px; z-index: 10000;">
                <div><strong>Admin Debug Panel</strong></div>
                <div>Requests in queue: <span id="debug-queue-count">${this.requestQueue.size}</span></div>
                <div>Debug mode: <span id="debug-mode-status">ON</span></div>
                <div>Last error: <span id="debug-last-error">None</span></div>
                <button onclick="adminInterface.clearDebugInfo()" style="margin-top: 0.5rem; padding: 0.25rem;">Clear</button>
                <button onclick="adminInterface.toggleDebugMode()" style="margin-top: 0.25rem; padding: 0.25rem;">Toggle Debug</button>
            </div>
        `;

        document.body.appendChild(debugPanel);

        // Update debug info periodically
        this.debugInterval = setInterval(() => {
            const queueCountEl = document.getElementById('debug-queue-count');
            if (queueCountEl) queueCountEl.textContent = this.requestQueue.size;
        }, 1000);
    }

    clearDebugInfo() {
        const lastErrorEl = document.getElementById('debug-last-error');
        if (lastErrorEl) lastErrorEl.textContent = 'None';
        this.logDebug('Debug info cleared');
    }

    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        localStorage.setItem('admin_debug_mode', this.debugMode.toString());

        const debugPanel = document.getElementById('admin-debug-panel');
        const modeStatusEl = document.getElementById('debug-mode-status');

        if (this.debugMode) {
            if (!debugPanel) this.showDebugPanel();
            if (modeStatusEl) modeStatusEl.textContent = 'ON';
            this.showMessage('Debug mode enabled', 'success');
        } else {
            if (debugPanel) debugPanel.remove();
            if (modeStatusEl) modeStatusEl.textContent = 'OFF';
            this.showMessage('Debug mode disabled', 'warning');
        }

        this.logDebug(`Debug mode ${this.debugMode ? 'enabled' : 'disabled'}`);
    }

    refreshPage() {
        // Refresh the page to show updated data
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    refreshPageWithCacheBust() {
        // Force cache-busting refresh
        const timestamp = Date.now();
        window.location.href = `${window.location.pathname}?_cb=${timestamp}`;
    }

    startConnectionMonitoring() {
        // Monitor connection status and show warnings for offline mode
        this.connectionCheckInterval = setInterval(() => {
            if (!navigator.onLine) {
                this.showMessage(
                    'Connection lost - changes may not be saved',
                    'warning',
                    {
                        persistent: true,
                        actionButton: {
                            text: 'Retry Connection',
                            onClick: () => window.location.reload()
                        }
                    }
                );
            }
        }, 5000);

        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.showMessage('Connection restored', 'success');
            this.logDebug('Connection restored');
        });

        window.addEventListener('offline', () => {
            this.showMessage('Connection lost', 'warning', { persistent: true });
            this.logDebug('Connection lost');
        });
    }

    // Enhanced error reporting for debugging save failures
    reportSaveFailure(error, requestData) {
        const errorReport = {
            timestamp: new Date().toISOString(),
            error: error.message || error,
            stack: error.stack,
            requestData: requestData,
            userAgent: navigator.userAgent,
            url: window.location.href,
            online: navigator.onLine,
            requestQueueSize: this.requestQueue.size
        };

        this.logError('Save failure report', errorReport);

        // Send error report to server if connection is available
        if (navigator.onLine) {
            this.sendErrorReport(errorReport);
        }
    }

    async sendErrorReport(errorReport) {
        try {
            await fetch('/api/report-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                body: JSON.stringify(errorReport)
            });
            this.logDebug('Error report sent to server');
        } catch (reportError) {
            this.logError('Failed to send error report', reportError);
        }
    }

    updateSummaryPanel() {
        // Update the summary panel counts and progress
        const assignedSelectors = document.querySelectorAll('.selector-badge.assigned').length;
        const totalSelectors = document.querySelectorAll('.selector-badge').length;
        const availableSelectors = totalSelectors - assignedSelectors;

        console.log('[ADMIN_DEBUG] updateSummaryPanel called:', { assignedSelectors, totalSelectors, availableSelectors });

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

    setupSearchFunctionality() {
        this.searchTimeout = null;
        this.currentSearchTerm = '';
        this.matchesGrid = document.getElementById('matches-grid');
        this.searchResultsInfo = document.getElementById('search-results-info');
        this.resultsCount = document.querySelector('.results-count');

        this.logDebug('Search functionality initialized');
    }

    handleTeamSearch(searchTerm) {
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Debounce search to avoid too many calls
        this.searchTimeout = setTimeout(() => {
            this.performTeamSearch(searchTerm);
        }, 300);
    }

    performTeamSearch(searchTerm) {
        this.currentSearchTerm = searchTerm.toLowerCase().trim();

        if (!this.matchesGrid) {
            this.logDebug('Matches grid not found');
            return;
        }

        const matchCards = this.matchesGrid.querySelectorAll('.match-card');
        let visibleCount = 0;
        let totalMatches = matchCards.length;

        if (this.currentSearchTerm === '') {
            // Show all matches if search is empty
            this.showAllMatches(matchCards);
            this.updateSearchResultsInfo(totalMatches, totalMatches);
            return;
        }

        // Filter matches based on search term
        matchCards.forEach(card => {
            const homeTeam = card.querySelector('.team.home')?.textContent.toLowerCase() || '';
            const awayTeam = card.querySelector('.team.away')?.textContent.toLowerCase() || '';
            const league = card.querySelector('.match-header h3')?.textContent.toLowerCase() || '';

            const matchesSearch = homeTeam.includes(this.currentSearchTerm) ||
                                awayTeam.includes(this.currentSearchTerm) ||
                                league.includes(this.currentSearchTerm);

            if (matchesSearch) {
                card.style.display = 'block';
                card.classList.add('search-match');
                visibleCount++;
            } else {
                card.style.display = 'none';
                card.classList.remove('search-match');
            }
        });

        // Update matches grid class and show results info
        this.matchesGrid.classList.toggle('search-filtered', this.currentSearchTerm !== '');
        this.updateSearchResultsInfo(totalMatches, visibleCount);

        // Show "no results" message if no matches found
        this.showNoResultsMessage(visibleCount === 0);

        this.logDebug('Team search performed', {
            searchTerm: this.currentSearchTerm,
            totalMatches,
            visibleCount
        });
    }

    showAllMatches(matchCards) {
        matchCards.forEach(card => {
            card.style.display = 'block';
            card.classList.remove('search-match');
        });

        this.matchesGrid.classList.remove('search-filtered');
        this.hideNoResultsMessage();
    }

    updateSearchResultsInfo(total, visible) {
        if (!this.searchResultsInfo || !this.resultsCount) return;

        if (this.currentSearchTerm === '') {
            this.searchResultsInfo.style.display = 'none';
            return;
        }

        this.resultsCount.textContent = `${visible} of ${total} matches`;
        this.searchResultsInfo.style.display = 'flex';

        this.logDebug('Search results updated', { total, visible });
    }

    showNoResultsMessage(show) {
        let noResultsDiv = this.matchesGrid.querySelector('.search-no-results');

        if (show && !noResultsDiv) {
            noResultsDiv = document.createElement('div');
            noResultsDiv.className = 'search-no-results';
            noResultsDiv.innerHTML = `
                <div class="search-no-results-icon">🔍</div>
                <h3>No matches found</h3>
                <p>No matches contain teams or leagues matching "${this.currentSearchTerm}"</p>
            `;
            this.matchesGrid.appendChild(noResultsDiv);
        } else if (!show && noResultsDiv) {
            noResultsDiv.remove();
        }
    }

    hideNoResultsMessage() {
        const noResultsDiv = this.matchesGrid.querySelector('.search-no-results');
        if (noResultsDiv) {
            noResultsDiv.remove();
        }
    }

    clearTeamSearch() {
        const teamSearchInput = document.getElementById('team-search');
        const clearSearchBtn = document.getElementById('clear-search');

        if (teamSearchInput) {
            teamSearchInput.value = '';
            this.performTeamSearch('');
            this.toggleClearButton('');
        }

        if (clearSearchBtn) {
            clearSearchBtn.style.display = 'none';
        }

        // Focus back to search input
        if (teamSearchInput) {
            teamSearchInput.focus();
        }

        this.logDebug('Team search cleared');
    }

    toggleClearButton(searchValue) {
        const clearSearchBtn = document.getElementById('clear-search');
        if (clearSearchBtn) {
            clearSearchBtn.style.display = searchValue.trim() !== '' ? 'block' : 'none';
        }
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

    // Show debug panel if debug mode is enabled
    if (admin.debugMode) {
        admin.showDebugPanel();
    }

    // Add enhanced keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // ESC key to close modal
        if (e.key === 'Escape') {
            admin.hideOverrideModal();
        }

        // Ctrl/Cmd + D to toggle debug mode
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            admin.toggleDebugMode();
        }

        // Ctrl/Cmd + R to refresh with cache busting
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            admin.refreshPageWithCacheBust();
        }
    });

    // Add connection status monitoring
    admin.startConnectionMonitoring();

    // Log initialization completion
    admin.logDebug('Admin interface fully initialized', {
        debugMode: admin.debugMode,
        requestQueueSize: admin.requestQueue.size,
        timestamp: new Date().toISOString()
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