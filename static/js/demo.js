// Demo Page JavaScript - Simplified Modern Tracker
// Author: Kilo Code
// Date: 2025

class DemoPage {
    constructor() {
        // State
        this.selections = new Map();
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

        // Initialize
        this.init();
    }

    async init() {
        console.log('🚀 Demo Page initialized');

        // Setup event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadCurrentWeek();
        await this.loadAllData();

        // Start auto-refresh
        this.startAutoRefresh();

        // Update UI
        this.updateLastUpdateTime();
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshDemoBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadAllData();
                this.showToast('Data refreshed successfully', 'success');
            });
        }

        // Auto-refresh toggle (if we add one later)
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + R to refresh
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                this.loadAllData();
                this.showToast('Data refreshed', 'success');
            }
        });
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
        const loadingState = document.getElementById('demoLoading');
        if (loadingState) loadingState.style.display = 'block';

        try {
            // Load unified data from modern endpoint
            const response = await fetch('/api/modern-tracker-data');
            const data = await response.json();

            if (data.success) {
                // Update state with unified data
                this.selections.clear();
                if (data.selections) {
                    Object.entries(data.selections).forEach(([selector, matchData]) => {
                        const enhancedMatchData = this.enhanceMatchData(matchData);
                        this.selections.set(selector, enhancedMatchData);
                    });
                }

                this.liveScores.clear();
                if (data.matches) {
                    Object.entries(data.matches).forEach(([selector, matchData]) => {
                        const enhancedMatchData = this.enhanceMatchData(matchData);
                        this.liveScores.set(selector, enhancedMatchData);
                    });
                }

                // Update all sections
                this.updateHeroStats(data);
                this.updateAccumulatorStatus(data);
                this.renderLiveMatches();

                // Update last update time
                this.updateLastUpdateTime();
            } else {
                // Handle fallback data
                if (data.fallback) {
                    console.warn('Using fallback data due to API error:', data.error);
                    this.handleFallbackData(data);
                    this.showToast('Using cached data - some features may be limited', 'warning');
                } else {
                    throw new Error(data.error || 'Failed to load data');
                }
            }
        } catch (error) {
            console.error('Error loading data:', error);
            this.showToast('Failed to load data - check connection', 'error');
        } finally {
            if (loadingState) loadingState.style.display = 'none';
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
        this.updateHeroStats(data);
        this.updateAccumulatorStatus(data);
        this.renderLiveMatches();
    }

    updateHeroStats(data = null) {
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
        document.getElementById('totalSelections').textContent = stats.totalSelections;
        document.getElementById('selectionProgressText').textContent = `${stats.completionPercentage}%`;

        // Update progress ring
        const progressRing = document.getElementById('selectionProgressRing');
        if (progressRing) {
            const circumference = 163.36;
            const offset = circumference - (stats.completionPercentage / 100) * circumference;
            progressRing.style.strokeDashoffset = offset;
        }

        document.getElementById('bttsSuccess').textContent = stats.bttsSuccess;
        document.getElementById('bttsPending').textContent = stats.bttsPending;
        document.getElementById('bttsFailed').textContent = stats.bttsFailed;

        // Update success rate
        const successRate = stats.totalSelections > 0
            ? Math.round((stats.bttsSuccess / stats.totalSelections) * 100)
            : 0;
        document.getElementById('bttsSuccessRate').textContent = `${successRate}%`;
    }

    updateAccumulatorStatus(data = null) {
        let stats = {
            bttsSuccess: 0,
            bttsPending: 0,
            bttsFailed: 0,
            totalSelections: this.selections.size
        };

        if (data && data.statistics) {
            stats = {
                bttsSuccess: data.statistics.btts_detected || 0,
                bttsPending: data.statistics.btts_pending || 0,
                bttsFailed: data.statistics.btts_failed || 0,
                totalSelections: data.statistics.selected_count || this.selections.size
            };
        } else {
            // Calculate manually
            this.liveScores.forEach((matchData) => {
                if (matchData.btts_detected) {
                    stats.bttsSuccess++;
                } else if (matchData.status === 'finished') {
                    stats.bttsFailed++;
                } else if (matchData.is_selected) {
                    stats.bttsPending++;
                }
            });
        }

        const statusElement = document.getElementById('accumulatorStatus');
        const messageElement = document.getElementById('statusMessage');

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

    renderLiveMatches() {
        const container = document.getElementById('liveMatchesGrid');
        if (!container) return;

        // Show empty state if no selections
        if (this.liveScores.size === 0) {
            document.getElementById('demoEmpty').style.display = 'block';
            container.innerHTML = '';
            return;
        }

        document.getElementById('demoEmpty').style.display = 'none';
        container.innerHTML = '';

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
            }
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
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

// Initialize demo when DOM is ready
let demo;
document.addEventListener('DOMContentLoaded', () => {
    demo = new DemoPage();
    window.demo = demo; // Make globally accessible
});