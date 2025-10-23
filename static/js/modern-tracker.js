// Modern Acca Tracker - Single Page Application
// Author: Kombai AI
// Date: 2025

class ModernAccaTracker {
    constructor() {
        // State
        this.currentTab = 'dashboard';
        this.selections = new Map();
        this.matches = [];
        this.liveScores = new Map();
        this.currentWeek = null;
        this.autoRefresh = true;
        this.refreshInterval = 30000; // 30 seconds
        this.refreshTimer = null;

        // Selectors list
        this.selectors = [
            "Glynny", "Eamonn Bone", "Mickey D", "Rob Carney",
            "Steve H", "Danny", "Eddie Lee", "Fran Radar"
        ];

        // Admin-like features
        this.debugMode = localStorage.getItem('modern_debug_mode') === 'true';
        this.requestQueue = new Map(); // Track ongoing requests to prevent race conditions
        this.overrideModal = null;
        this.selectedReason = null;
        this.errorReports = [];

        // Initialize
        this.init();
    }
    
    async init() {
        console.log('🚀 Modern Acca Tracker initialized');

        // Setup event listeners
        this.setupEventListeners();

        // Initialize debug mode
        if (this.debugMode) {
            this.showDebugPanel();
        }

        // Load initial data
        await this.loadCurrentWeek();
        await this.loadAllData();

        // Start auto-refresh
        this.startAutoRefresh();

        // Update UI
        this.updateConnectionStatus('connected');

        // Start connection monitoring
        this.startConnectionMonitoring();

        this.logDebug('Modern Acca Tracker fully initialized', {
            debugMode: this.debugMode,
            requestQueueSize: this.requestQueue.size,
            selectionsCount: this.selections.size,
            timestamp: new Date().toISOString()
        });
    }
    
    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-button, .mobile-nav-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Quick actions
        document.querySelectorAll('.action-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleQuickAction(action);
            });
        });

        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('autoRefreshToggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.autoRefresh = e.target.checked;
                if (this.autoRefresh) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // Debug mode toggle
        const debugModeToggle = document.getElementById('debugModeToggle');
        if (debugModeToggle) {
            debugModeToggle.checked = this.debugMode;
            debugModeToggle.addEventListener('change', (e) => {
                this.toggleDebugMode();
            });
        }

        // Modal close handlers
        document.getElementById('closeAssignmentModal')?.addEventListener('click', () => {
            this.closeAssignmentModal();
        });

        document.getElementById('cancelAssignment')?.addEventListener('click', () => {
            this.closeAssignmentModal();
        });

        document.getElementById('confirmAssignment')?.addEventListener('click', () => {
            this.confirmAssignment();
        });

        // Override modal handlers
        document.getElementById('closeOverrideModal')?.addEventListener('click', () => {
            this.closeOverrideModal();
        });

        document.getElementById('cancelOverride')?.addEventListener('click', () => {
            this.closeOverrideModal();
        });

        document.getElementById('confirmOverride')?.addEventListener('click', () => {
            this.confirmOverride();
        });

        document.getElementById('overrideBtn')?.addEventListener('click', () => {
            this.showOverrideModal();
        });

        // Debug panel handlers
        document.getElementById('clearDebugBtn')?.addEventListener('click', () => {
            this.clearDebugInfo();
        });

        document.getElementById('toggleDebugBtn')?.addEventListener('click', () => {
            this.toggleDebugMode();
        });

        document.getElementById('testConnectionBtn')?.addEventListener('click', () => {
            this.testConnection();
        });

        document.getElementById('refreshDataBtn')?.addEventListener('click', () => {
            this.loadAllData();
        });

        // Click outside modals to close
        document.getElementById('assignmentModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'assignmentModal') {
                this.closeAssignmentModal();
            }
        });

        document.getElementById('overrideModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'overrideModal') {
                this.closeOverrideModal();
            }
        });

        // Override form validation
        document.getElementById('overrideConfirm')?.addEventListener('input', () => {
            this.validateOverrideForm();
        });

        document.querySelectorAll('input[name="override-reason"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.selectedReason = e.target.value;
                this.validateOverrideForm();
            });
        });

        // Direct assignment dropdowns
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('selector-dropdown')) {
                this.handleDirectAssignment(e.target);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // ESC key to close modals
            if (e.key === 'Escape') {
                this.closeAssignmentModal();
                this.closeOverrideModal();
            }

            // Ctrl/Cmd + D to toggle debug mode
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                this.toggleDebugMode();
            }

            // Ctrl/Cmd + R to refresh with cache busting
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                this.refreshPageWithCacheBust();
            }
        });
    }
    
    switchTab(tabName) {
        this.currentTab = tabName;
        
        // Update tab buttons
        document.querySelectorAll('.tab-button, .mobile-nav-button').forEach(button => {
            button.classList.toggle('active', button.dataset.tab === tabName);
        });
        
        // Update content sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.toggle('active', section.id === `${tabName}Section`);
        });
        
        // Load data for the active tab
        if (tabName === 'selection') {
            this.loadSelectionData();
        } else if (tabName === 'tracker') {
            this.loadTrackerData();
        }
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    handleQuickAction(action) {
        switch (action) {
            case 'goto-selection':
                this.switchTab('selection');
                break;
            case 'goto-tracker':
                this.switchTab('tracker');
                break;
            case 'refresh':
                this.loadAllData();
                this.showToast('Data refreshed successfully', 'success');
                break;
        }
    }
    
    async loadCurrentWeek() {
        try {
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            if (data.success && data.week) {
                this.currentWeek = data.week;
                const weekElement = document.getElementById('currentWeek');
                if (weekElement) {
                    weekElement.textContent = new Date(data.week).toLocaleDateString('en-US', {
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric'
                    });
                }
            } else if (data.fallback && data.week) {
                // Handle fallback data
                console.warn('Using fallback week data');
                this.currentWeek = data.week;
                const weekElement = document.getElementById('currentWeek');
                if (weekElement) {
                    weekElement.textContent = new Date(data.week).toLocaleDateString('en-US', {
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric'
                    });
                }
            }
        } catch (error) {
            console.error('Error loading current week:', error);
            // Set fallback week if API fails
            const fallbackWeek = new Date().toISOString().split('T')[0];
            this.currentWeek = fallbackWeek;
            const weekElement = document.getElementById('currentWeek');
            if (weekElement) {
                weekElement.textContent = new Date(fallbackWeek).toLocaleDateString('en-US', {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric'
                });
            }
        }
    }
    
    async loadAllData() {
        this.updateConnectionStatus('loading');

        try {
            // Load unified data from modern endpoint
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            if (data.success) {
                // Update state with unified data - handle enhanced structure
                this.selections.clear();
                if (data.selections) {
                    Object.entries(data.selections).forEach(([selector, matchData]) => {
                        // Ensure backward compatibility and handle null/undefined values
                        const enhancedMatchData = this.enhanceMatchData(matchData);
                        this.selections.set(selector, enhancedMatchData);
                    });
                }

                this.liveScores.clear();
                if (data.matches) {
                    Object.entries(data.matches).forEach(([selector, matchData]) => {
                        // Ensure backward compatibility and handle null/undefined values
                        const enhancedMatchData = this.enhanceMatchData(matchData);
                        this.liveScores.set(selector, enhancedMatchData);
                    });
                }

                // Update all sections with enhanced data
                this.updateDashboard(data);
                this.updateSelectionProgress(data);

                // Update last update time
                this.updateLastUpdateTime();

                this.updateConnectionStatus('connected');
            } else {
                // Handle enhanced error response with fallback data
                if (data.fallback) {
                    console.warn('Using fallback data due to API error:', data.error);
                    this.handleFallbackData(data);
                    this.updateConnectionStatus('connected');
                    this.showToast('Using cached data - some features may be limited', 'warning');
                } else {
                    throw new Error(data.error || 'Failed to load data');
                }
            }
        } catch (error) {
            console.error('Error loading data:', error);
            this.updateConnectionStatus('disconnected');
            this.showToast('Failed to load data - check connection', 'error');
        }
    }
    
    async loadSelections() {
        try {
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            if (data.success && data.selections) {
                this.selections.clear();
                Object.entries(data.selections).forEach(([selector, matchData]) => {
                    const enhancedMatchData = this.enhanceMatchData(matchData);
                    this.selections.set(selector, enhancedMatchData);
                });
            } else if (data.fallback && data.selections) {
                // Handle fallback data
                console.warn('Using fallback selections data');
                this.selections.clear();
                Object.entries(data.selections).forEach(([selector, matchData]) => {
                    const enhancedMatchData = this.enhanceMatchData(matchData);
                    this.selections.set(selector, enhancedMatchData);
                });
            }
        } catch (error) {
            console.error('Error loading selections:', error);
            throw error;
        }
    }
    
    async loadSelectionData() {
        const loadingState = document.getElementById('selectionLoading');
        if (loadingState) loadingState.classList.add('active');

        console.log('[MODERN_DEBUG] Starting loadSelectionData');

        try {
            // Load unified data from modern endpoint
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            console.log('[MODERN_DEBUG] loadSelectionData API response:', data);

            if (data.success) {
                // Update selections with enhanced data processing
                this.selections.clear();
                if (data.selections) {
                    Object.entries(data.selections).forEach(([selector, matchData]) => {
                        const enhancedMatchData = this.enhanceMatchData(matchData);
                        this.selections.set(selector, enhancedMatchData);
                    });
                }
                console.log('[MODERN_DEBUG] Selections loaded:', this.selections.size);

                // Load available matches from BBC matches for current week with enhanced error handling
                try {
                    const currentWeek = this.currentWeek || new Date().toISOString().split('T')[0];
                    const matchesResponse = await fetch(`/api/bbc-matches/${currentWeek}`);
                    const matchesData = await matchesResponse.json();

                    console.log('[MODERN_DEBUG] BBC matches response:', matchesData);

                    if (matchesData.success) {
                        // Filter for 15:00 matches to match admin interface behavior
                        const allMatches = matchesData.fixtures || [];
                        this.matches = allMatches.filter(match => match.kickoff === '15:00');
                        console.log(`[MODERN_DEBUG] Filtered to ${this.matches.length} 15:00 matches from ${allMatches.length} total matches`);
                    } else if (matchesData.fallback) {
                        console.warn('[MODERN_DEBUG] Using fallback matches data');
                        const allMatches = matchesData.fixtures || [];
                        this.matches = allMatches.filter(match => match.kickoff === '15:00');
                        this.showToast('Using cached matches - may not be current', 'warning');
                    }
                } catch (matchesError) {
                    console.warn('[MODERN_DEBUG] Error loading matches, continuing without:', matchesError);
                    this.matches = [];
                }

                // Render selectors
                this.renderSelectors();

                // Render available matches
                this.renderAvailableMatches();

                // Update progress with enhanced data
                this.updateSelectionProgress(data);
            } else {
                // Handle enhanced error response with fallback data
                if (data.fallback) {
                    console.warn('[MODERN_DEBUG] Using fallback data for selections:', data.error);
                    this.selections.clear();
                    if (data.selections) {
                        Object.entries(data.selections).forEach(([selector, matchData]) => {
                            const enhancedMatchData = this.enhanceMatchData(matchData);
                            this.selections.set(selector, enhancedMatchData);
                        });
                    }
                    this.matches = [];
                    this.renderSelectors();
                    this.renderAvailableMatches();
                    this.updateSelectionProgress(data);
                    this.showToast('Using cached data - selections may be outdated', 'warning');
                } else {
                    throw new Error(data.error || 'Failed to load selection data');
                }
            }

        } catch (error) {
            console.error('[MODERN_DEBUG] Error loading selection data:', error);
            this.showToast('Failed to load matches - check connection', 'error');
        } finally {
            if (loadingState) loadingState.classList.remove('active');
        }
    }
    
    async loadTrackerData() {
        const loadingState = document.getElementById('trackerLoading');
        if (loadingState) loadingState.classList.add('active');

        try {
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            if (data.success && data.matches) {
                this.liveScores.clear();
                Object.entries(data.matches).forEach(([selector, matchData]) => {
                    // Enhanced match data handling
                    const enhancedMatchData = this.enhanceMatchData(matchData);
                    this.liveScores.set(selector, enhancedMatchData);
                });

                // Render live matches
                this.renderLiveMatches();

                // Update tracker summary with enhanced data
                this.updateTrackerSummary(data);
            } else {
                // Handle enhanced error response with fallback data
                if (data.fallback) {
                    console.warn('Using fallback data for tracker:', data.error);
                    this.liveScores.clear();
                    if (data.matches) {
                        Object.entries(data.matches).forEach(([selector, matchData]) => {
                            const enhancedMatchData = this.enhanceMatchData(matchData);
                            this.liveScores.set(selector, enhancedMatchData);
                        });
                    }
                    this.renderLiveMatches();
                    this.updateTrackerSummary(data);
                    this.showToast('Using cached data - live updates may be limited', 'warning');
                } else {
                    throw new Error(data.error || 'Failed to load tracker data');
                }
            }

        } catch (error) {
            console.error('Error loading tracker data:', error);
            this.showToast('Failed to load live data - check connection', 'error');
        } finally {
            if (loadingState) loadingState.classList.remove('active');
        }
    }
    
    enhanceMatchData(matchData) {
        // Ensure backward compatibility and handle null/undefined values
        if (!matchData || typeof matchData !== 'object') {
            return {
                home_team: null,
                away_team: null,
                prediction: 'TBD',
                confidence: 5,
                assigned_at: null,
                league: null,
                status: 'no_selection',
                home_score: 0,
                away_score: 0,
                match_time: '—',
                btts_detected: false,
                is_selected: false,
                placeholder_text: 'No data available',
                last_updated: new Date().toISOString()
            };
        }

        return {
            home_team: matchData.home_team || null,
            away_team: matchData.away_team || null,
            prediction: matchData.prediction || 'TBD',
            confidence: matchData.confidence || 5,
            assigned_at: matchData.assigned_at || null,
            league: matchData.league || null,
            status: matchData.status || 'not_started',
            home_score: matchData.home_score || 0,
            away_score: matchData.away_score || 0,
            match_time: matchData.match_time || '0\'',
            btts_detected: Boolean(matchData.btts_detected),
            is_selected: Boolean(matchData.is_selected),
            placeholder_text: matchData.placeholder_text || null,
            error: matchData.error || false,
            error_message: matchData.error_message || null,
            last_updated: matchData.last_updated || new Date().toISOString()
        };
    }

    handleFallbackData(data) {
        // Handle fallback data from API error responses
        console.warn('Processing fallback data:', data);

        // Update selections with fallback data
        this.selections.clear();
        if (data.selections) {
            Object.entries(data.selections).forEach(([selector, matchData]) => {
                const enhancedMatchData = this.enhanceMatchData(matchData);
                this.selections.set(selector, enhancedMatchData);
            });
        }

        // Update live scores with fallback data
        this.liveScores.clear();
        if (data.matches) {
            Object.entries(data.matches).forEach(([selector, matchData]) => {
                const enhancedMatchData = this.enhanceMatchData(matchData);
                this.liveScores.set(selector, enhancedMatchData);
            });
        }

        // Update UI with fallback data
        this.updateDashboard(data);
        this.updateSelectionProgress(data);
    }

    updateDashboard(data = null) {
        // Use enhanced statistics from backend if available, otherwise calculate manually
        let stats = {
            totalSelections: this.selections.size,
            completionPercentage: 0,
            bttsSuccess: 0,
            bttsPending: 0,
            bttsFailed: 0
        };

        // Use backend statistics if available
        if (data && data.statistics) {
            stats = {
                totalSelections: data.statistics.selected_count || this.selections.size,
                completionPercentage: data.statistics.completion_percentage || 0,
                bttsSuccess: data.statistics.btts_detected || 0,
                bttsPending: data.statistics.btts_pending || 0,
                bttsFailed: data.statistics.btts_failed || 0
            };
        } else {
            // Calculate manually for backward compatibility
            const totalSelections = this.selections.size;
            const maxSelections = 8;
            stats.completionPercentage = Math.round((totalSelections / maxSelections) * 100);

            // Calculate BTTS stats from live scores
            this.liveScores.forEach((matchData) => {
                if (matchData.btts_detected) {
                    stats.bttsSuccess++;
                } else if (matchData.status === 'finished') {
                    stats.bttsFailed++;
                } else {
                    stats.bttsPending++;
                }
            });
        }

        // Update stats display
        document.getElementById('dashTotalSelections').textContent = stats.totalSelections;
        document.getElementById('selectionProgressText').textContent = `${stats.completionPercentage}%`;

        // Update progress ring
        const progressRing = document.getElementById('selectionProgressRing');
        if (progressRing) {
            const circumference = 163.36;
            const offset = circumference - (stats.completionPercentage / 100) * circumference;
            progressRing.style.strokeDashoffset = offset;
        }

        document.getElementById('dashBttsSuccess').textContent = stats.bttsSuccess;
        document.getElementById('dashBttsPending').textContent = stats.bttsPending;
        document.getElementById('dashBttsFailed').textContent = stats.bttsFailed;

        // Update success rate
        const successRate = stats.totalSelections > 0
            ? Math.round((stats.bttsSuccess / stats.totalSelections) * 100)
            : 0;
        document.getElementById('bttsSuccessRate').textContent = `${successRate}%`;

        // Update accumulator status
        this.updateAccumulatorStatus('dashAccumulatorStatus', 'dashStatusMessage', {
            bttsSuccess: stats.bttsSuccess,
            bttsPending: stats.bttsPending,
            bttsFailed: stats.bttsFailed,
            totalSelections: stats.totalSelections
        });
    }
    
    updateAccumulatorStatus(statusElementId, messageElementId, stats) {
        const statusElement = document.getElementById(statusElementId);
        const messageElement = document.getElementById(messageElementId);
        
        if (!statusElement) return;
        
        let statusClass = 'pending';
        let statusIcon = '⏳';
        let statusText = 'PENDING';
        let message = 'Awaiting match selections and live results';
        
        if (stats.bttsFailed > 0) {
            statusClass = 'failed';
            statusIcon = '❌';
            statusText = 'FAILED';
            message = `Accumulator failed - ${stats.bttsFailed} match(es) without BTTS`;
        } else if (stats.bttsSuccess === stats.totalSelections && stats.totalSelections > 0) {
            statusClass = 'success';
            statusIcon = '✅';
            statusText = 'SUCCESS';
            message = 'All matches achieved BTTS! 🎉';
        } else if (stats.bttsSuccess > 0) {
            statusClass = 'in-progress';
            statusIcon = '⚡';
            statusText = 'IN PROGRESS';
            message = `${stats.bttsSuccess} of ${stats.totalSelections} matches with BTTS`;
        }
        
        statusElement.className = `status-badge-large ${statusClass}`;
        statusElement.innerHTML = `
            <span class="status-icon">${statusIcon}</span>
            <span class="status-text">${statusText}</span>
        `;
        
        if (messageElement) {
            messageElement.textContent = message;
        }
    }
    
    renderSelectors() {
        const container = document.getElementById('selectorsGrid');
        if (!container) return;

        container.innerHTML = '';

        this.selectors.forEach(selector => {
            const isAssigned = this.selections.has(selector);
            const matchData = this.selections.get(selector) || {};

            const card = document.createElement('div');
            card.className = `selector-card ${isAssigned ? 'assigned' : ''}`;

            let assignmentHTML = '';
            let actionsHTML = '';

            if (isAssigned && matchData) {
                // Enhanced assignment display with better timestamp handling
                const assignedTime = matchData.assigned_at
                    ? new Date(matchData.assigned_at).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    })
                    : 'Recently';

                const homeTeam = matchData.home_team || 'TBD';
                const awayTeam = matchData.away_team || 'TBD';
                const league = matchData.league || 'Unknown League';

                assignmentHTML = `
                    <div class="selector-assignment">
                        <div class="assignment-match">
                            <div class="match-teams">${homeTeam} vs ${awayTeam}</div>
                            <div class="match-league">${league}</div>
                        </div>
                        <div class="assignment-time">
                            <span class="time-label">Assigned:</span>
                            <span class="time-value">${assignedTime}</span>
                        </div>
                        ${matchData.error ? `
                            <div class="assignment-error">
                                <span class="error-icon">⚠️</span>
                                <span class="error-text">${matchData.error_message || 'Data error'}</span>
                            </div>
                        ` : ''}
                    </div>
                `;
                actionsHTML = `
                    <div class="selector-actions">
                        <button class="btn btn-small btn-danger" onclick="app.unassignMatch('${selector}')">
                            Unassign
                        </button>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="selector-header">
                    <div class="selector-name">${selector}</div>
                    <div class="selector-status ${isAssigned ? 'assigned' : 'available'}">
                        ${isAssigned ? '✓ Assigned' : 'Available'}
                    </div>
                </div>
                ${assignmentHTML}
                ${actionsHTML}
            `;

            container.appendChild(card);
        });
    }
    
    renderAvailableMatches() {
        const container = document.getElementById('availableMatchesGrid');
        if (!container) return;

        container.innerHTML = '';

        if (!this.matches || this.matches.length === 0) {
            container.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">⚽</div>
                    <h3>No Matches Available</h3>
                    <p style="color: var(--color-text-secondary); margin-top: 0.5rem;">
                        No 15:00 matches available for selection at this time
                    </p>
                </div>
            `;
            return;
        }

        this.matches.forEach((match, index) => {
            // Enhanced match validation
            if (!match || typeof match !== 'object') {
                console.warn(`Invalid match data at index ${index}:`, match);
                return;
            }

            const homeTeam = match.home_team || 'Unknown Team';
            const awayTeam = match.away_team || 'Unknown Team';
            const matchId = `${match.league || 'Unknown'}_${homeTeam}_${awayTeam}`;

            // Enhanced assignment checking
            const isAssigned = Array.from(this.selections.values()).some(
                m => m && m.home_team === homeTeam && m.away_team === awayTeam
            );

            const card = document.createElement('div');
            card.className = `match-card ${isAssigned ? 'assigned' : ''}`;

            // Enhanced match display with error handling
            const league = match.league || 'Unknown League';
            const kickoff = match.kickoff || '15:00';

            let assignmentHTML = '';
            if (isAssigned) {
                // Show assigned badge for already assigned matches
                const assignedSelector = Array.from(this.selections.entries()).find(
                    ([selector, m]) => m && m.home_team === homeTeam && m.away_team === awayTeam
                );
                const selectorName = assignedSelector ? assignedSelector[0] : 'Unknown';
                assignmentHTML = `
                    <div class="match-assigned-badge">
                        ✓ Assigned to ${selectorName}
                    </div>
                `;
            } else {
                // Show direct assignment dropdown for unassigned matches
                const availableSelectors = this.selectors.filter(selector => !this.selections.has(selector));
                assignmentHTML = `
                    <div class="match-assignment">
                        <div class="assignment-controls">
                            <select class="selector-dropdown" data-match-id="${matchId}">
                                <option value="">Select Selector ▼</option>
                                ${availableSelectors.map(selector =>
                                    `<option value="${selector}">${selector}</option>`
                                ).join('')}
                            </select>
                            <div class="assignment-status" style="display: none;">
                                <span class="status-text"></span>
                                <span class="status-spinner" style="display: none;">⟳</span>
                            </div>
                        </div>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="match-league">${league}</div>
                <div class="match-teams">
                    ${homeTeam} vs ${awayTeam}
                </div>
                <div class="match-time">
                    Kickoff: ${kickoff}
                </div>
                ${match.error ? `
                    <div class="match-error">
                        <span class="error-icon">⚠️</span>
                        <span class="error-text">${match.error_message || 'Data error'}</span>
                    </div>
                ` : ''}
                ${assignmentHTML}
            `;

            container.appendChild(card);
        });
    }
    
    renderLiveMatches() {
        const container = document.getElementById('liveMatchesGrid');
        if (!container) return;

        container.innerHTML = '';

        if (this.liveScores.size === 0) {
            container.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">⚽</div>
                    <h3>No Live Matches</h3>
                    <p style="color: var(--color-text-secondary); margin-top: 0.5rem;">
                        Matches will appear here once they start
                    </p>
                </div>
            `;
            return;
        }

        this.selectors.forEach(selector => {
            const matchData = this.liveScores.get(selector);

            // Enhanced match data handling with better fallbacks
            const enhancedMatchData = matchData || this.createPlaceholderMatchData(selector);

            if (!matchData) {
                this.liveScores.set(selector, enhancedMatchData);
            }

            const card = document.createElement('div');

            // Enhanced BTTS status determination
            let cardClass = 'live-match-card btts-pending';
            let bttsStatusClass = 'pending';
            let bttsStatusText = 'AWAITING GOALS';
            let statusIcon = '⏳';

            if (enhancedMatchData.error) {
                cardClass = 'live-match-card error';
                bttsStatusClass = 'error';
                bttsStatusText = '⚠️ ERROR';
                statusIcon = '⚠️';
            } else if (enhancedMatchData.btts_detected) {
                cardClass = 'live-match-card btts-success';
                bttsStatusClass = 'success';
                bttsStatusText = '✓ BOTH SCORED';
                statusIcon = '✅';
            } else if (enhancedMatchData.status === 'finished') {
                cardClass = 'live-match-card btts-failed';
                bttsStatusClass = 'failed';
                bttsStatusText = '✗ NO BTTS';
                statusIcon = '❌';
            } else if (enhancedMatchData.home_score > 0 || enhancedMatchData.away_score > 0) {
                bttsStatusText = 'ONE SCORED';
                statusIcon = '🔄';
            } else if (enhancedMatchData.status === 'no_selection') {
                bttsStatusText = 'NO SELECTION';
                statusIcon = '⭕';
            }

            card.className = cardClass;

            const homeScore = enhancedMatchData.home_score || 0;
            const awayScore = enhancedMatchData.away_score || 0;
            const matchTime = this.formatMatchTime(enhancedMatchData);
            const homeTeam = enhancedMatchData.home_team || 'TBD';
            const awayTeam = enhancedMatchData.away_team || 'TBD';
            const league = enhancedMatchData.league || 'Unknown League';

            card.innerHTML = `
                <div class="live-selector-name">${selector}</div>
                <div class="live-match-league">${league}</div>
                <div class="live-match-teams">
                    ${homeTeam} vs ${awayTeam}
                </div>
                <div class="live-score-display">
                    <div class="live-score">${homeScore} - ${awayScore}</div>
                    <div class="live-time">${matchTime}</div>
                </div>
                <div class="live-btts-status ${bttsStatusClass}">
                    <span class="status-icon">${statusIcon}</span>
                    <span class="status-text">${bttsStatusText}</span>
                </div>
                <div class="live-match-status">
                    ${this.formatMatchStatus(enhancedMatchData.status)}
                </div>
                ${enhancedMatchData.placeholder_text ? `
                    <div class="live-placeholder-text">${enhancedMatchData.placeholder_text}</div>
                ` : ''}
                ${enhancedMatchData.error_message ? `
                    <div class="live-error-text">Error: ${enhancedMatchData.error_message}</div>
                ` : ''}
            `;

            container.appendChild(card);
        });
    }

    createPlaceholderMatchData(selector) {
        return {
            home_team: null,
            away_team: null,
            home_score: 0,
            away_score: 0,
            status: 'no_selection',
            match_time: '—',
            league: null,
            btts_detected: false,
            is_selected: false,
            placeholder_text: 'Awaiting Match Assignment',
            error: false,
            error_message: null,
            last_updated: new Date().toISOString()
        };
    }
    
    updateTrackerSummary(data) {
        // Use enhanced statistics from backend if available
        let stats = {
            btts_detected: 0,
            btts_pending: 0,
            btts_failed: 0,
            selected_count: this.selections.size,
            completion_percentage: 0,
            live_matches: 0,
            finished_matches: 0,
            not_started_matches: 0
        };

        if (data && data.statistics) {
            stats = { ...stats, ...data.statistics };
        } else {
            // Calculate manually for backward compatibility
            this.liveScores.forEach((matchData) => {
                if (matchData.btts_detected) {
                    stats.btts_detected++;
                } else if (matchData.status === 'finished') {
                    stats.btts_failed++;
                } else if (matchData.is_selected) {
                    stats.btts_pending++;
                }
            });
        }

        // Update display elements
        const successElement = document.getElementById('trackerBttsSuccess');
        const pendingElement = document.getElementById('trackerBttsPending');
        const failedElement = document.getElementById('trackerBttsFailed');

        if (successElement) successElement.textContent = stats.btts_detected;
        if (pendingElement) pendingElement.textContent = stats.btts_pending;
        if (failedElement) failedElement.textContent = stats.btts_failed;

        // Update accumulator status with enhanced data
        this.updateAccumulatorStatus('trackerAccumulatorStatus', null, {
            bttsSuccess: stats.btts_detected,
            bttsPending: stats.btts_pending,
            bttsFailed: stats.btts_failed,
            totalSelections: stats.selected_count
        });
    }
    
    updateSelectionProgress(data = null) {
        // Use enhanced statistics from backend if available
        let assigned = this.selections.size;
        let total = 8;
        let percentage = 0;

        console.log('[MODERN_DEBUG] updateSelectionProgress called:', { data, assigned, total });

        if (data && data.statistics) {
            assigned = data.statistics.selected_count || this.selections.size;
            percentage = data.statistics.completion_percentage || 0;
        } else {
            // Calculate manually for backward compatibility
            percentage = Math.round((assigned / total) * 100);
        }

        console.log('[MODERN_DEBUG] Progress calculated:', { assigned, total, percentage });

        // Update basic progress display
        document.getElementById('assignedCount').textContent = assigned;

        const progressBar = document.getElementById('assignmentProgressBar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }

        const progressPercentage = document.getElementById('progressPercentage');
        if (progressPercentage) {
            progressPercentage.textContent = `${percentage}%`;
        }

        // Update enhanced progress details
        this.updateProgressDetails(assigned, total);

        // Show/hide override warning
        this.updateOverrideWarning(assigned);
    }

    updateProgressDetails(assigned, total) {
        const progressDetails = document.getElementById('progressDetails');
        if (!progressDetails) return;

        const remaining = total - assigned;
        let detailsHTML = '';

        if (assigned === 0) {
            detailsHTML = '<span class="progress-detail">No selections made yet</span>';
        } else if (remaining === 0) {
            detailsHTML = '<span class="progress-detail success">All selections complete! 🎉</span>';
        } else if (remaining <= 2) {
            detailsHTML = `<span class="progress-detail warning">Still need ${remaining} more selection${remaining !== 1 ? 's' : ''}</span>`;
        } else {
            detailsHTML = `<span class="progress-detail">Still need ${remaining} more selections</span>`;
        }

        progressDetails.innerHTML = detailsHTML;
    }

    updateOverrideWarning(assigned) {
        const overrideWarning = document.getElementById('overrideWarning');
        const currentSelectionsCount = document.getElementById('currentSelectionsCount');

        if (assigned < 8) {
            if (overrideWarning) overrideWarning.style.display = 'block';
            if (currentSelectionsCount) currentSelectionsCount.textContent = assigned;
        } else {
            if (overrideWarning) overrideWarning.style.display = 'none';
        }
    }
    
    formatMatchTime(matchData) {
        const status = matchData.status;
        
        if (status === 'not_started' || status === 'no_selection') {
            return 'Not Started';
        } else if (status === 'finished') {
            return 'FT';
        } else if (status === 'live') {
            return matchData.match_time || 'LIVE';
        } else if (status === 'half_time') {
            return 'HT';
        }
        
        return status?.toUpperCase() || 'TBD';
    }
    
    formatMatchStatus(status) {
        const statusMap = {
            'not_started': 'Not Started',
            'live': 'LIVE',
            'finished': 'Finished',
            'half_time': 'Half Time',
            'no_selection': 'Awaiting Selection'
        };
        
        return statusMap[status] || status?.toUpperCase() || 'Unknown';
    }
    
    openAssignmentModal(match) {
        // Legacy method - kept for backward compatibility
        // New direct assignment system doesn't use modals
        const modal = document.getElementById('assignmentModal');
        const detailsContainer = document.getElementById('assignmentDetails');
        const selectorSelect = document.getElementById('selectorSelect');

        if (!modal || !detailsContainer || !selectorSelect) return;

        // Store match data
        modal.dataset.matchData = JSON.stringify(match);

        // Update details
        detailsContainer.innerHTML = `
            <p><strong>League:</strong> ${match.league || 'Unknown'}</p>
            <p><strong>Match:</strong> ${match.home_team} vs ${match.away_team}</p>
            <p><strong>Kickoff:</strong> ${match.kickoff || '15:00'}</p>
        `;

        // Update selector dropdown
        selectorSelect.innerHTML = '<option value="">Choose a selector...</option>';
        this.selectors.forEach(selector => {
            if (!this.selections.has(selector)) {
                const option = document.createElement('option');
                option.value = selector;
                option.textContent = selector;
                selectorSelect.appendChild(option);
            }
        });

        // Show modal
        modal.classList.add('active');
    }

    async handleDirectAssignment(dropdown) {
        const matchCard = dropdown.closest('.match-card');
        const statusDiv = matchCard.querySelector('.assignment-status');
        const statusText = statusDiv?.querySelector('.status-text');
        const statusSpinner = statusDiv?.querySelector('.status-spinner');
        const selector = dropdown.value;

        console.log('[MODERN_DEBUG] handleDirectAssignment called:', { selector, matchId: dropdown.dataset.matchId });

        if (!selector) {
            // Reset status if no selector selected
            if (statusDiv) statusDiv.style.display = 'none';
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
        if (statusDiv) {
            statusDiv.style.display = 'flex';
            if (statusText) statusText.textContent = `Assigning to ${selector}...`;
            if (statusSpinner) statusSpinner.style.display = 'inline-block';
        }

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
                if (statusText) {
                    statusText.textContent = `✓ Assigned to ${selector}`;
                    statusText.style.color = '#4caf50';
                }
                if (statusSpinner) statusSpinner.style.display = 'none';
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
                if (reqStatusText) {
                    reqStatusText.textContent = `✗ ${errorMessage}`;
                    reqStatusText.style.color = '#f44336';
                }
                if (reqStatusSpinner) reqStatusSpinner.style.display = 'none';
            }
        });

        this.logError(`Assignment failed for ${requestKey}`, error);

        // Reset dropdown after error
        setTimeout(() => {
            dropdown.value = '';
            if (statusDiv) statusDiv.style.display = 'none';

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
    
    closeAssignmentModal() {
        const modal = document.getElementById('assignmentModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    showOverrideModal() {
        const modal = document.getElementById('overrideModal');
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';

            // Reset form
            const confirmInput = document.getElementById('overrideConfirm');
            if (confirmInput) confirmInput.value = '';

            const confirmBtn = document.getElementById('confirmOverride');
            if (confirmBtn) confirmBtn.disabled = true;

            // Update current count
            const currentCount = document.getElementById('overrideCurrentCount');
            if (currentCount) currentCount.textContent = this.selections.size;

            this.selectedReason = null;
        }
    }

    closeOverrideModal() {
        const modal = document.getElementById('overrideModal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = 'auto';
        }
    }

    validateOverrideForm() {
        const confirmInput = document.getElementById('overrideConfirm');
        const confirmBtn = document.getElementById('confirmOverride');

        const requiredText = "I confirm that I want to proceed with fewer than 8 selections";
        const isTextValid = confirmInput && confirmInput.value === requiredText;
        const isReasonSelected = this.selectedReason !== null;

        if (confirmBtn) {
            confirmBtn.disabled = !(isTextValid && isReasonSelected);
        }

        return isTextValid && isReasonSelected;
    }

    async confirmOverride() {
        if (!this.validateOverrideForm()) {
            this.showToast('Please complete all confirmation requirements', 'error');
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
                this.showToast('Override confirmed successfully', 'success');
                this.closeOverrideModal();
                this.refreshPage();
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('Network error occurred', 'error');
            console.error('Override error:', error);
        }
    }
    
    async confirmAssignment() {
        // Legacy method - kept for backward compatibility with modal system
        const modal = document.getElementById('assignmentModal');
        const selectorSelect = document.getElementById('selectorSelect');

        if (!modal || !selectorSelect) return;

        const selector = selectorSelect.value;
        if (!selector) {
            this.showToast('Please select a selector', 'error');
            return;
        }

        const matchData = JSON.parse(modal.dataset.matchData || '{}');
        const matchId = `${matchData.league}_${matchData.home_team}_${matchData.away_team}`;

        try {
            const response = await fetch('/api/assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    match_id: matchId,
                    selector: selector,
                    timestamp: new Date().toISOString()
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showToast(`Match assigned to ${selector}`, 'success');
                this.closeAssignmentModal();

                // Reload data
                await this.loadAllData();
                this.loadSelectionData();
            } else {
                this.showToast(data.error || 'Failed to assign match', 'error');
            }
        } catch (error) {
            console.error('Error assigning match:', error);
            this.showToast('Failed to assign match', 'error');
        }
    }

    logDebug(message, data = null) {
        if (this.debugMode) {
            const timestamp = new Date().toISOString();
            console.log(`[MODERN_DEBUG ${timestamp}] ${message}`, data || '');
        }
    }

    logError(message, error = null) {
        const timestamp = new Date().toISOString();
        console.error(`[MODERN_ERROR ${timestamp}] ${message}`, error || '');
        this.logDebug('Error occurred', { message, error: error?.stack || error });

        // Add to error reports
        this.errorReports.push({
            timestamp,
            message,
            error: error?.message || error,
            stack: error?.stack,
            url: window.location.href,
            userAgent: navigator.userAgent
        });

        // Keep only last 50 errors
        if (this.errorReports.length > 50) {
            this.errorReports.shift();
        }
    }

    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        localStorage.setItem('modern_debug_mode', this.debugMode.toString());

        const debugPanel = document.getElementById('debugPanel');
        const debugModeToggle = document.getElementById('debugModeToggle');

        if (this.debugMode) {
            if (debugPanel) debugPanel.style.display = 'block';
            if (debugModeToggle) debugModeToggle.checked = true;
            this.showDebugPanel();
            this.showToast('Debug mode enabled', 'success');
        } else {
            if (debugPanel) debugPanel.style.display = 'none';
            if (debugModeToggle) debugModeToggle.checked = false;
            this.hideDebugPanel();
            this.showToast('Debug mode disabled', 'warning');
        }

        this.logDebug(`Debug mode ${this.debugMode ? 'enabled' : 'disabled'}`);
    }

    showDebugPanel() {
        if (!this.debugMode) return;

        // Update debug info
        this.updateDebugInfo();

        // Show debug panel
        const debugPanel = document.getElementById('debugPanel');
        if (debugPanel) {
            debugPanel.style.display = 'block';
        }

        // Update debug info periodically
        this.debugInterval = setInterval(() => {
            this.updateDebugInfo();
        }, 1000);
    }

    hideDebugPanel() {
        const debugPanel = document.getElementById('debugPanel');
        if (debugPanel) {
            debugPanel.style.display = 'none';
        }

        if (this.debugInterval) {
            clearInterval(this.debugInterval);
            this.debugInterval = null;
        }
    }

    updateDebugInfo() {
        const queueCountEl = document.getElementById('debugQueueCount');
        const lastErrorEl = document.getElementById('debugLastError');
        const connectionEl = document.getElementById('debugConnectionStatus');
        const selectionsEl = document.getElementById('debugTotalSelections');

        if (queueCountEl) queueCountEl.textContent = this.requestQueue.size;
        if (lastErrorEl) {
            const lastError = this.errorReports.length > 0 ? this.errorReports[this.errorReports.length - 1].message : 'None';
            lastErrorEl.textContent = lastError;
        }
        if (connectionEl) connectionEl.textContent = navigator.onLine ? 'Online' : 'Offline';
        if (selectionsEl) selectionsEl.textContent = this.selections.size;
    }

    clearDebugInfo() {
        this.errorReports = [];
        const lastErrorEl = document.getElementById('debugLastError');
        if (lastErrorEl) lastErrorEl.textContent = 'None';
        this.logDebug('Debug info cleared');
    }

    async testConnection() {
        try {
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            if (data.success) {
                this.showToast('Connection test successful', 'success');
                this.logDebug('Connection test passed');
            } else {
                throw new Error(data.error || 'Connection test failed');
            }
        } catch (error) {
            this.showToast('Connection test failed', 'error');
            this.logError('Connection test failed', error);
        }
    }

    refreshPageWithCacheBust() {
        // Force cache-busting refresh
        const timestamp = Date.now();
        window.location.href = `${window.location.pathname}?_cb=${timestamp}`;
    }
    
    async unassignMatch(selector) {
        if (!confirm(`Are you sure you want to unassign ${selector}'s match?`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/unassign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ selector })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Match unassigned from ${selector}`, 'success');
                
                // Reload data
                await this.loadAllData();
                this.loadSelectionData();
            } else {
                this.showToast(data.error || 'Failed to unassign match', 'error');
            }
        } catch (error) {
            console.error('Error unassigning match:', error);
            this.showToast('Failed to unassign match', 'error');
        }
    }
    
    updateConnectionStatus(status) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (!statusDot || !statusText) return;
        
        statusDot.className = 'status-dot';
        
        switch (status) {
            case 'connected':
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusDot.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                break;
            case 'loading':
                statusText.textContent = 'Loading...';
                break;
        }
    }
    
    updateLastUpdateTime() {
        const timeElement = document.getElementById('lastUpdateTime');
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString();
        }
    }
    
    startAutoRefresh() {
        this.stopAutoRefresh();

        this.refreshTimer = setInterval(() => {
            if (this.autoRefresh) {
                this.loadAllData();

                // Reload current tab data
                if (this.currentTab === 'tracker') {
                    this.loadTrackerData();
                }
            }
        }, this.refreshInterval);
    }

    startConnectionMonitoring() {
        // Monitor connection status and show warnings for offline mode
        this.connectionCheckInterval = setInterval(() => {
            if (!navigator.onLine) {
                this.showToast(
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
            this.showToast('Connection restored', 'success');
            this.logDebug('Connection restored');
        });

        window.addEventListener('offline', () => {
            this.showToast('Connection lost', 'warning', { persistent: true });
            this.logDebug('Connection lost');
        });
    }
    
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    validateDataStructure(data) {
        // Validate that the API response has the expected structure
        if (!data || typeof data !== 'object') {
            return false;
        }

        // Check for required fields in successful response
        if (data.success) {
            return true; // Trust the backend's success flag
        }

        // Check for fallback data structure
        if (data.fallback && data.matches && data.statistics) {
            return true;
        }

        return false;
    }

    handleApiError(error, context = 'API call') {
        console.error(`Error in ${context}:`, error);

        // Enhanced error reporting
        this.logError(`API Error in ${context}`, error);

        // Determine error type and provide appropriate user feedback
        let errorMessage = 'An unexpected error occurred';
        let errorType = 'error';

        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = 'Network connection failed - check your internet connection';
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Server is not responding - please try again later';
        } else if (error.message.includes('JSON')) {
            errorMessage = 'Invalid response from server - data may be corrupted';
            errorType = 'warning';
        } else if (error.message) {
            errorMessage = error.message;
        }

        this.showToast(errorMessage, errorType);
        this.updateConnectionStatus('disconnected');

        return errorMessage;
    }

    showToast(message, type = 'info', options = {}) {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const {
            duration = type === 'warning' ? 4000 : 3000,
            persistent = false,
            actionButton = null
        } = options;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const iconMap = {
            success: '✓',
            error: '✗',
            warning: '⚠️',
            info: 'ℹ️'
        };

        let toastHTML = `
            <div class="toast-icon">${iconMap[type] || 'ℹ️'}</div>
            <div class="toast-message">${message}</div>
        `;

        // Add action button if provided
        if (actionButton) {
            toastHTML += `
                <div class="toast-actions">
                    <button class="toast-action-btn" onclick="${actionButton.onClick}">${actionButton.text}</button>
                </div>
            `;
        }

        toast.innerHTML = toastHTML;
        container.appendChild(toast);

        // Auto remove after duration (unless persistent)
        if (!persistent) {
            setTimeout(() => {
                toast.style.animation = 'slideInRight 0.3s reverse';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        // Store reference for potential manual removal
        toast.remove = () => {
            toast.style.animation = 'slideInRight 0.3s reverse';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        };

        return toast;
    }
}

// Initialize app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new ModernAccaTracker();
    window.app = app; // Make globally accessible
});