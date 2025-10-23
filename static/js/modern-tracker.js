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
        
        // Initialize
        this.init();
    }
    
    async init() {
        console.log('🚀 Modern Acca Tracker initialized');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.loadCurrentWeek();
        await this.loadAllData();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Update UI
        this.updateConnectionStatus('connected');
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
        
        // Modal close
        document.getElementById('closeAssignmentModal')?.addEventListener('click', () => {
            this.closeAssignmentModal();
        });
        
        document.getElementById('cancelAssignment')?.addEventListener('click', () => {
            this.closeAssignmentModal();
        });
        
        document.getElementById('confirmAssignment')?.addEventListener('click', () => {
            this.confirmAssignment();
        });
        
        // Click outside modal to close
        document.getElementById('assignmentModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'assignmentModal') {
                this.closeAssignmentModal();
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
            const response = await fetch('/api/tracker-data');
            const data = await response.json();
            
            if (data.success && data.week) {
                this.currentWeek = data.week;
                document.getElementById('currentWeek')?.textContent = 
                    new Date(data.week).toLocaleDateString('en-US', { 
                        month: 'long', 
                        day: 'numeric', 
                        year: 'numeric' 
                    });
            }
        } catch (error) {
            console.error('Error loading current week:', error);
        }
    }
    
    async loadAllData() {
        this.updateConnectionStatus('loading');
        
        try {
            // Load selections
            await this.loadSelections();
            
            // Update all sections
            this.updateDashboard();
            
            // Update last update time
            this.updateLastUpdateTime();
            
            this.updateConnectionStatus('connected');
        } catch (error) {
            console.error('Error loading data:', error);
            this.updateConnectionStatus('disconnected');
            this.showToast('Failed to load data', 'error');
        }
    }
    
    async loadSelections() {
        try {
            const response = await fetch('/api/selections');
            const data = await response.json();
            
            if (data.selectors) {
                this.selections.clear();
                Object.entries(data.selectors).forEach(([selector, matchData]) => {
                    this.selections.set(selector, matchData);
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
        
        try {
            // Load available matches
            const response = await fetch('/api/bbc-fixtures');
            const data = await response.json();
            
            if (data.success && data.matches) {
                this.matches = data.matches;
            }
            
            // Render selectors
            this.renderSelectors();
            
            // Render available matches
            this.renderAvailableMatches();
            
            // Update progress
            this.updateSelectionProgress();
            
        } catch (error) {
            console.error('Error loading selection data:', error);
            this.showToast('Failed to load matches', 'error');
        } finally {
            if (loadingState) loadingState.classList.remove('active');
        }
    }
    
    async loadTrackerData() {
        const loadingState = document.getElementById('trackerLoading');
        if (loadingState) loadingState.classList.add('active');
        
        try {
            const response = await fetch('/api/btts-status');
            const data = await response.json();
            
            if (data.matches) {
                this.liveScores.clear();
                Object.entries(data.matches).forEach(([selector, matchData]) => {
                    this.liveScores.set(selector, matchData);
                });
            }
            
            // Render live matches
            this.renderLiveMatches();
            
            // Update tracker summary
            this.updateTrackerSummary(data);
            
        } catch (error) {
            console.error('Error loading tracker data:', error);
            this.showToast('Failed to load live data', 'error');
        } finally {
            if (loadingState) loadingState.classList.remove('active');
        }
    }
    
    updateDashboard() {
        const totalSelections = this.selections.size;
        const maxSelections = 8;
        const percentage = Math.round((totalSelections / maxSelections) * 100);
        
        // Update stats
        document.getElementById('dashTotalSelections').textContent = totalSelections;
        document.getElementById('selectionProgressText').textContent = `${percentage}%`;
        
        // Update progress ring
        const progressRing = document.getElementById('selectionProgressRing');
        if (progressRing) {
            const circumference = 163.36;
            const offset = circumference - (percentage / 100) * circumference;
            progressRing.style.strokeDashoffset = offset;
        }
        
        // Calculate BTTS stats
        let bttsSuccess = 0;
        let bttsPending = 0;
        let bttsFailed = 0;
        
        this.liveScores.forEach((matchData) => {
            if (matchData.btts_detected) {
                bttsSuccess++;
            } else if (matchData.status === 'finished') {
                bttsFailed++;
            } else {
                bttsPending++;
            }
        });
        
        document.getElementById('dashBttsSuccess').textContent = bttsSuccess;
        document.getElementById('dashBttsPending').textContent = bttsPending;
        document.getElementById('dashBttsFailed').textContent = bttsFailed;
        
        // Update success rate
        const successRate = totalSelections > 0 
            ? Math.round((bttsSuccess / totalSelections) * 100) 
            : 0;
        document.getElementById('bttsSuccessRate').textContent = `${successRate}%`;
        
        // Update accumulator status
        this.updateAccumulatorStatus('dashAccumulatorStatus', 'dashStatusMessage', {
            bttsSuccess,
            bttsPending,
            bttsFailed,
            totalSelections
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
            const matchData = this.selections.get(selector);
            
            const card = document.createElement('div');
            card.className = `selector-card ${isAssigned ? 'assigned' : ''}`;
            
            let assignmentHTML = '';
            let actionsHTML = '';
            
            if (isAssigned && matchData) {
                assignmentHTML = `
                    <div class="selector-assignment">
                        <div class="assignment-match">
                            ${matchData.home_team} vs ${matchData.away_team}
                        </div>
                        <div class="assignment-time">
                            Assigned: ${new Date(matchData.assigned_at || Date.now()).toLocaleString()}
                        </div>
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
                        ${isAssigned ? 'Assigned' : 'Available'}
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
        
        if (this.matches.length === 0) {
            container.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
                    <p style="color: var(--color-text-secondary); font-size: 1.125rem;">
                        No matches available for selection
                    </p>
                </div>
            `;
            return;
        }
        
        this.matches.forEach(match => {
            const matchId = `${match.league}_${match.home_team}_${match.away_team}`;
            const isAssigned = Array.from(this.selections.values()).some(
                m => m.home_team === match.home_team && m.away_team === match.away_team
            );
            
            const card = document.createElement('div');
            card.className = `match-card ${isAssigned ? 'assigned' : ''}`;
            
            if (!isAssigned) {
                card.style.cursor = 'pointer';
                card.addEventListener('click', () => {
                    this.openAssignmentModal(match);
                });
            }
            
            card.innerHTML = `
                <div class="match-league">${match.league || 'Unknown League'}</div>
                <div class="match-teams">
                    ${match.home_team} vs ${match.away_team}
                </div>
                <div class="match-time">
                    Kickoff: ${match.kickoff || '15:00'}
                </div>
                ${isAssigned ? '<div class="match-assigned-badge">Assigned</div>' : ''}
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
            
            if (!matchData) return;
            
            const card = document.createElement('div');
            
            let cardClass = 'live-match-card btts-pending';
            let bttsStatusClass = 'pending';
            let bttsStatusText = 'AWAITING GOALS';
            
            if (matchData.btts_detected) {
                cardClass = 'live-match-card btts-success';
                bttsStatusClass = 'success';
                bttsStatusText = '✓ BOTH SCORED';
            } else if (matchData.status === 'finished') {
                cardClass = 'live-match-card btts-failed';
                bttsStatusClass = 'failed';
                bttsStatusText = '✗ NO BTTS';
            } else if (matchData.home_score > 0 || matchData.away_score > 0) {
                bttsStatusText = 'ONE SCORED';
            }
            
            card.className = cardClass;
            
            const homeScore = matchData.home_score || 0;
            const awayScore = matchData.away_score || 0;
            const matchTime = this.formatMatchTime(matchData);
            
            card.innerHTML = `
                <div class="live-selector-name">${selector}</div>
                <div class="live-match-league">${matchData.league || 'Unknown League'}</div>
                <div class="live-match-teams">
                    ${matchData.home_team || 'TBD'} vs ${matchData.away_team || 'TBD'}
                </div>
                <div class="live-score-display">
                    <div class="live-score">${homeScore} - ${awayScore}</div>
                    <div class="live-time">${matchTime}</div>
                </div>
                <div class="live-btts-status ${bttsStatusClass}">
                    ${bttsStatusText}
                </div>
                <div class="live-match-status">
                    ${this.formatMatchStatus(matchData.status)}
                </div>
            `;
            
            container.appendChild(card);
        });
    }
    
    updateTrackerSummary(data) {
        const stats = data.statistics || {};
        
        document.getElementById('trackerBttsSuccess').textContent = stats.btts_detected || 0;
        document.getElementById('trackerBttsPending').textContent = stats.btts_pending || 0;
        document.getElementById('trackerBttsFailed').textContent = stats.btts_failed || 0;
        
        this.updateAccumulatorStatus('trackerAccumulatorStatus', null, {
            bttsSuccess: stats.btts_detected || 0,
            bttsPending: stats.btts_pending || 0,
            bttsFailed: stats.btts_failed || 0,
            totalSelections: this.selections.size
        });
    }
    
    updateSelectionProgress() {
        const assigned = this.selections.size;
        const total = 8;
        const percentage = Math.round((assigned / total) * 100);
        
        document.getElementById('assignedCount').textContent = assigned;
        
        const progressBar = document.getElementById('assignmentProgressBar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
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
    
    closeAssignmentModal() {
        const modal = document.getElementById('assignmentModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }
    
    async confirmAssignment() {
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
    
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const iconMap = {
            success: '✓',
            error: '✗',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">${iconMap[type] || 'ℹ'}</div>
            <div class="toast-message">${message}</div>
        `;
        
        container.appendChild(toast);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new ModernAccaTracker();
    window.app = app; // Make globally accessible
});