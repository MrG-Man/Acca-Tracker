// Modern Acca Tracker - Single Page Application
// Author: Kombai AI
// Date: 2025

class ModernAccaTracker {
    constructor() {
        // State
        this.currentTab = 'tracker'; // Default to tracker view
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
        this.errorReports = [];

        // Team colors for logos
        this.teamColors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
        ];

        // Initialize
        this.init();
    }

    getTeamColor(teamName) {
        if (!teamName) return '#666666';
        const hash = teamName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return this.teamColors[hash % this.teamColors.length];
    }
    
    async init() {
        console.log('🚀 Modern Acca Tracker initialized');

        // Setup event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadCurrentWeek();
        await this.loadAllData();

        // Load tracker data directly
        await this.loadTrackerData();

        // Start auto-refresh
        this.startAutoRefresh();

        // Update UI
        this.updateConnectionStatus('connected');

        // Start connection monitoring
        this.startConnectionMonitoring();

        console.log('Modern Acca Tracker fully initialized');
    }
    
    setupEventListeners() {
        document.getElementById('refreshDataBtn')?.addEventListener('click', () => {
            this.loadAllData();
            this.loadTrackerData();
        });
    }
    
    switchTab(tabName) {
        this.currentTab = tabName;

        // Since we only have tracker view now, just load tracker data
        if (tabName === 'tracker') {
            this.loadTrackerData();
        }

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    handleQuickAction(action) {
        switch (action) {
            case 'refresh':
                this.loadAllData();
                this.loadTrackerData();
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

                // Update connection status and other global elements
                this.updateConnectionStatus('connected');
                this.updateLastUpdateTime();
            } else {
                // Handle enhanced error response with fallback data
                if (data.fallback) {
                    console.warn('Using fallback data due to API error:', data.error);
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
    
    // Removed loadSelections function as it's not needed in mobile layout
    
    // Removed loadSelectionData function as it's not needed in mobile layout
    
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

    // Removed handleFallbackData function as it's not needed in mobile layout

    updateDashboard(data = null) {
        // Dashboard functionality removed in mobile layout
        // Just update connection status and last update time
        this.updateConnectionStatus('connected');
        this.updateLastUpdateTime();
    }
    
    // Removed updateAccumulatorStatus function as it's not needed in mobile layout
    
    // Removed renderSelectors function as it's not needed in mobile layout
    
    // Removed renderAvailableMatches function as it's not needed in mobile layout
    
    renderLiveMatches() {
        const container = document.getElementById('liveMatchesGrid');
        if (!container) return;

        container.innerHTML = '';

        if (this.liveScores.size === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚽</div>
                    <div class="empty-state-text">
                        <h3>No Live Matches</h3>
                        <p>Matches will appear here once they start</p>
                    </div>
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
            card.className = 'match-card';

            // Enhanced BTTS status determination
            const homeScore = enhancedMatchData.home_score || 0;
            const awayScore = enhancedMatchData.away_score || 0;
            const matchTime = this.formatMatchTime(enhancedMatchData);
            const homeTeam = enhancedMatchData.home_team || 'TBD';
            const awayTeam = enhancedMatchData.away_team || 'TBD';
            const homeColor = this.getTeamColor(homeTeam);
            const awayColor = this.getTeamColor(awayTeam);

            // BTTS badge
            let bttsBadge = '';
            if (enhancedMatchData.btts_detected) {
                bttsBadge = '<div class="btts-badge">BTTS ✓</div>';
            }

            card.innerHTML = `
                <div class="match-header">
                    <div class="selector-name">${selector}</div>
                    <div class="match-status">${matchTime}</div>
                </div>

                <div class="match-teams">
                    <div class="team home-team">
                        <div class="team-logo" style="background-color: ${homeColor};"></div>
                        <span class="team-name">${homeTeam}</span>
                    </div>

                    <div class="match-score">
                        <span class="score">${homeScore} - ${awayScore}</span>
                    </div>

                    <div class="team away-team">
                        <span class="team-name">${awayTeam}</span>
                        <div class="team-logo" style="background-color: ${awayColor};"></div>
                    </div>
                </div>

                ${bttsBadge}
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
    
    // Removed updateTrackerSummary function as it's not needed in mobile layout
    
    updateSelectionProgress(data = null) {
        // Selection progress functionality removed in mobile layout
        // Just update connection status
        this.updateConnectionStatus('connected');
    }

    // Removed updateProgressDetails and updateOverrideWarning functions
    // as they are not needed in the mobile layout
    
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
    
    // Removed openAssignmentModal function as modals are not used in mobile layout

    // Removed handleDirectAssignment function as assignment is not available in mobile layout

    // Removed assignment-related functions as they are not needed in mobile layout
    
    // Removed modal functions as they are not needed in mobile layout

    // Removed override and assignment functions as they are not needed in mobile layout

    logError(message, error = null) {
        const timestamp = new Date().toISOString();
        console.error(`[MODERN_ERROR ${timestamp}] ${message}`, error || '');

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



    // Removed refreshPageWithCacheBust function as it's not needed in mobile layout
    
    // Removed unassignMatch function as assignment is not available in mobile layout
    
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
                this.loadTrackerData();
            }
        }, this.refreshInterval);
    }

    startConnectionMonitoring() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.showToast('Connection restored', 'success');
        });

        window.addEventListener('offline', () => {
            this.showToast('Connection lost', 'warning', { persistent: true });
        });
    }
    
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        if (this.connectionCheckInterval) {
            clearInterval(this.connectionCheckInterval);
            this.connectionCheckInterval = null;
        }
    }
    
    // Removed validateDataStructure and handleApiError functions as they're not essential for mobile layout

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