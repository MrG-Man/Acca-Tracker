// BTTS Accumulator Tracker - Real-time Update Logic

class BTTSTracker {
    constructor() {
        this.matchesContainer = document.getElementById('matches-container');
        this.loadingState = document.getElementById('loading-state');
        this.errorState = document.getElementById('error-state');
        this.connectionStatus = document.getElementById('connection-status');
        this.lastUpdated = document.getElementById('last-updated');
        this.accumulatorStatus = document.getElementById('accumulator-status');
        this.bttsSuccessCount = document.getElementById('btts-success-count');
        this.bttsPendingCount = document.getElementById('btts-pending-count');
        this.bttsFailedCount = document.getElementById('btts-failed-count');

        // Configuration
        this.updateInterval = 30000; // 30 seconds
        this.retryInterval = 5000; // 5 seconds
        this.maxRetries = 3;

        // State
        this.currentData = null;
        this.updateTimer = null;
        this.retryCount = 0;
        this.isConnected = false;

        // Initialize
        this.init();
    }

    init() {
        console.log('🎯 Enhanced BTTS Tracker initialized');
        this.showLoading();
        this.startUpdates();
        this.bindEvents();
        this.addKeyboardShortcuts();
        this.startPerformanceMetrics();
    }

    addKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ignore if user is typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch(e.key.toLowerCase()) {
                case 'r':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.refresh();
                    }
                    break;
                case 'c':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.triggerConfetti();
                    }
                    break;
                case 'd':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        console.log('Current tracker data:', this.getCurrentData());
                    }
                    break;
            }
        });
    }

    startPerformanceMetrics() {
        // Track performance metrics
        this.metrics = {
            updatesReceived: 0,
            errorsEncountered: 0,
            lastUpdateTime: null,
            averageUpdateTime: 0
        };

        // Update metrics every 10 updates
        setInterval(() => {
            this.updatePerformanceDisplay();
        }, 30000);
    }

    updatePerformanceDisplay() {
        const metricsContainer = document.getElementById('performance-metrics');
        if (metricsContainer) {
            metricsContainer.innerHTML = `
                <div class="metrics-item">
                    <span class="metrics-label">Updates:</span>
                    <span class="metrics-value">${this.metrics.updatesReceived}</span>
                </div>
                <div class="metrics-item">
                    <span class="metrics-label">Avg Time:</span>
                    <span class="metrics-value">${Math.round(this.metrics.averageUpdateTime)}ms</span>
                </div>
            `;
        }
    }

    bindEvents() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });

        // Handle online/offline events
        window.addEventListener('online', () => {
            console.log('🌐 Connection restored');
            this.retryCount = 0;
            this.updateConnectionStatus(true);
            this.resumeUpdates();
        });

        window.addEventListener('offline', () => {
            console.log('🌐 Connection lost');
            this.updateConnectionStatus(false);
            this.pauseUpdates();
        });

        // Handle error state retry button
        const retryButton = this.errorState?.querySelector('button');
        if (retryButton) {
            retryButton.addEventListener('click', () => {
                this.retryCount = 0;
                this.showLoading();
                this.fetchData();
            });
        }
    }

    startUpdates() {
        // Initial fetch
        this.fetchData();

        // Set up periodic updates
        this.updateTimer = setInterval(() => {
            this.fetchData();
        }, this.updateInterval);
    }

    pauseUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }

    resumeUpdates() {
        if (!this.updateTimer) {
            this.startUpdates();
        }
    }

    async fetchData() {
        try {
            console.log('📡 Fetching BTTS data...');
            this.updateConnectionStatus('loading');

            const endpoint = '/api/btts-status';
            console.log(`📡 Using endpoint: ${endpoint}`);

            const response = await fetch(endpoint);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ BTTS data received:', data);
            console.log('🔍 DEBUG: Full data object:', JSON.stringify(data, null, 2));

            this.retryCount = 0;
            this.isConnected = true;
            this.updateConnectionStatus(true);
            this.processData(data);

        } catch (error) {
            console.error('❌ Error fetching BTTS data:', error);
            this.handleError(error);
        }
    }

    processData(data) {
        const startTime = performance.now();
        console.log('🔍 DEBUG: processData called with data:', data);
        console.log('🔍 DEBUG: data.status:', data.status);
        console.log('🔍 DEBUG: data.matches:', data.matches);
        this.currentData = data;

        // Update performance metrics
        this.metrics.updatesReceived++;
        this.metrics.lastUpdateTime = performance.now();

        if (this.metrics.updatesReceived > 1) {
            this.metrics.averageUpdateTime = (this.metrics.averageUpdateTime * (this.metrics.updatesReceived - 1) + (performance.now() - startTime)) / this.metrics.updatesReceived;
        } else {
            this.metrics.averageUpdateTime = performance.now() - startTime;
        }

        // Handle different data statuses
        if (data.status === 'NO_SELECTIONS' && (!data.matches || Object.keys(data.matches).length === 0)) {
            this.handleNoSelections(data);
            return;
        }

        // Update last updated timestamp
        const now = new Date();
        this.lastUpdated.textContent = now.toLocaleTimeString();

        // Check for BTTS events before updating display
        this.detectBTTSChanges(data);

        // Update accumulator summary
        this.updateAccumulatorSummary(data);

        // Update matches display
        this.updateMatchesDisplay(data);

        // Hide loading/error states
        this.hideLoading();
        this.hideError();

        console.log(`✅ Data processed in ${Math.round(performance.now() - startTime)}ms`);
    }

    updateAccumulatorSummary(data) {
        // Handle no selections case
        if (data.status === 'NO_SELECTIONS') {
            this.accumulatorStatus.innerHTML = `
                <span class="status-badge pending">
                    AWAITING SELECTIONS
                </span>
            `;
            this.bttsSuccessCount.textContent = '0';
            this.bttsPendingCount.textContent = '0';
            this.bttsFailedCount.textContent = '0';
            return;
        }

        const stats = data.statistics || {};
        const accumulatorStatus = data.accumulator_status || 'PENDING';

        // Update counts with fallback calculation if API doesn't provide them
        const successCount = stats.btts_detected || this.calculateSuccessCount(data.matches || {});
        const pendingCount = stats.btts_pending || this.calculatePendingCount(data.matches || {});
        const failedCount = stats.btts_failed || this.calculateFailedCount(data.matches || {});

        this.bttsSuccessCount.textContent = successCount;
        this.bttsPendingCount.textContent = pendingCount;
        this.bttsFailedCount.textContent = failedCount;

        // Determine overall accumulator status based on match states
        const calculatedStatus = this.calculateAccumulatorStatus(data.matches || {});

        // Update accumulator status
        const statusMap = {
            'SUCCESS': { class: 'success', text: '✅ SUCCESS' },
            'FAILED': { class: 'failed', text: '❌ FAILED' },
            'IN_PROGRESS': { class: 'pending', text: '⏳ IN PROGRESS' },
            'PENDING': { class: 'pending', text: '⏳ PENDING' },
            'ERROR': { class: 'failed', text: '⚠️ ERROR' }
        };

        const statusInfo = statusMap[calculatedStatus] || statusMap[accumulatorStatus] || statusMap['PENDING'];

        this.accumulatorStatus.innerHTML = `
            <span class="status-badge ${statusInfo.class}">
                ${statusInfo.text}
            </span>
        `;

        // Add celebration animation for success
        if (calculatedStatus === 'SUCCESS') {
            this.triggerCelebration();
        }
    }

    calculateSuccessCount(matches) {
        return Object.values(matches).filter(match => match.btts_detected).length;
    }

    calculatePendingCount(matches) {
        return Object.values(matches).filter(match =>
            match.status === 'live' && !match.btts_detected
        ).length;
    }

    calculateFailedCount(matches) {
        return Object.values(matches).filter(match =>
            match.status === 'finished' && !match.btts_detected
        ).length;
    }

    calculateAccumulatorStatus(matches) {
        const matchArray = Object.values(matches);
        if (matchArray.length === 0) return 'PENDING';

        const hasFailed = matchArray.some(match => match.status === 'finished' && !match.btts_detected);
        const hasPending = matchArray.some(match => match.status === 'live' && !match.btts_detected);
        const allSuccessful = matchArray.every(match => match.btts_detected);

        if (hasFailed) return 'FAILED';
        if (allSuccessful) return 'SUCCESS';
        if (hasPending) return 'IN_PROGRESS';
        return 'PENDING';
    }

    detectBTTSChanges(data) {
        const matches = data.matches || {};
        const previousData = this.currentData;

        if (!previousData || !previousData.matches) {
            return;
        }

        const previousMatches = previousData.matches || {};

        // Check each match for BTTS events
        Object.entries(matches).forEach(([selectorName, matchData]) => {
            const previousMatchData = previousMatches[selectorName];
            if (!previousMatchData) return;

            const card = document.getElementById(`match-${selectorName}`);
            if (!card) return;

            const currentHomeScore = matchData.home_score || 0;
            const currentAwayScore = matchData.away_score || 0;
            const previousHomeScore = previousMatchData.home_score || 0;
            const previousAwayScore = previousMatchData.away_score || 0;

            // Check if BTTS condition was just met
            const currentBTTS = currentHomeScore > 0 && currentAwayScore > 0;
            const previousBTTS = previousHomeScore > 0 && previousAwayScore > 0;

            if (currentBTTS && !previousBTTS) {
                // BTTS was just achieved!
                this.triggerBTTSHighlight(card, selectorName, matchData);
            } else if ((currentHomeScore > previousHomeScore) || (currentAwayScore > previousAwayScore)) {
                // A goal was scored
                this.triggerGoalHighlight(card, matchData);
            }
        });
    }

    triggerBTTSHighlight(card, selectorName, matchData) {
        console.log(`🎯 BTTS detected for ${selectorName}!`);

        // Add enhanced highlight animation
        card.classList.add('btts-highlight');
        card.style.transform = 'scale(1.08)';
        card.style.boxShadow = '0 15px 50px rgba(40, 167, 69, 0.4)';

        // Update BTTS status with enhanced celebration
        const bttsStatus = card.querySelector('.btts-status');
        if (bttsStatus) {
            bttsStatus.classList.add('celebrating');
            bttsStatus.style.animation = 'bttsPulse 1.5s ease-in-out';
        }

        // Create success burst effect
        this.createSuccessBurst(card);

        // Trigger enhanced celebration effects
        setTimeout(() => {
            this.triggerEnhancedCelebration();
        }, 300);

        // Reset animation after delay
        setTimeout(() => {
            card.classList.remove('btts-highlight');
            card.style.transform = '';
            card.style.boxShadow = '';
            if (bttsStatus) {
                bttsStatus.classList.remove('celebrating');
                bttsStatus.style.animation = '';
            }
        }, 4000);
    }

    createSuccessBurst(card) {
        const burst = document.createElement('div');
        burst.className = 'success-burst';
        burst.style.left = '50%';
        burst.style.top = '50%';
        card.appendChild(burst);

        setTimeout(() => {
            if (burst.parentNode) {
                burst.remove();
            }
        }, 2000);
    }

    triggerEnhancedCelebration() {
        // Enhanced celebration with multiple effects
        this.triggerConfetti();

        // Add floating messages
        this.showFloatingMessage('🎉 BTTS SUCCESS! 🎉');

        // Animate statistics
        this.animateStatistics();

        // Play notification sound
        this.playNotificationSound();
    }

    showFloatingMessage(message) {
        const floatingMsg = document.createElement('div');
        floatingMsg.className = 'floating-message';
        floatingMsg.textContent = message;
        floatingMsg.style.cssText = `
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 15px 30px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
            box-shadow: 0 10px 30px rgba(40, 167, 69, 0.3);
            z-index: 10000;
            animation: floatMessage 4s ease-in-out forwards;
            border: 3px solid rgba(255, 255, 255, 0.3);
        `;

        document.body.appendChild(floatingMsg);

        setTimeout(() => {
            if (floatingMsg.parentNode) {
                floatingMsg.remove();
            }
        }, 4000);
    }

    animateStatistics() {
        const statValues = document.querySelectorAll('.stat-value');
        statValues.forEach((stat, index) => {
            setTimeout(() => {
                stat.classList.add('stat-updated');
                setTimeout(() => {
                    stat.classList.remove('stat-updated');
                }, 800);
            }, index * 100);
        });
    }

    triggerGoalHighlight(card, matchData) {
        // Add subtle goal animation
        card.classList.add('goal-highlight');
        card.style.transform = 'scale(1.02)';

        setTimeout(() => {
            card.classList.remove('goal-highlight');
            card.style.transform = '';
        }, 1000);
    }

    updateMatchesDisplay(data) {
        const matches = data.matches || {};
        console.log('🔍 DEBUG: updateMatchesDisplay called with matches:', matches);
        console.log('🔍 DEBUG: Number of matches:', Object.keys(matches).length);

        // Sort matches by selector name for consistent display
        const sortedMatches = Object.entries(matches).sort((a, b) => {
            return a[0].localeCompare(b[0]); // a[0] is the selector name (key)
        });

        console.log('🔍 DEBUG: sortedMatches length:', sortedMatches.length);
        if (sortedMatches.length === 0) {
            console.log('🔍 DEBUG: No matches found, calling showNoMatches');
            this.showNoMatches();
            return;
        }

        // Update existing cards or create new ones
        sortedMatches.forEach(([selectorName, matchData]) => {
            const existingCard = document.getElementById(`match-${selectorName}`);

            if (existingCard) {
                this.updateExistingMatchCard(existingCard, selectorName, matchData);
            } else {
                const matchCard = this.createMatchCard(selectorName, matchData);
                this.matchesContainer.appendChild(matchCard);
            }
        });

        // Remove cards for matches that no longer exist
        const currentSelectorNames = new Set(sortedMatches.map(([name]) => name));
        const existingCards = this.matchesContainer.querySelectorAll('.match-card');
        existingCards.forEach(card => {
            const selectorName = card.id.replace('match-', '');
            if (!currentSelectorNames.has(selectorName)) {
                card.remove();
            }
        });
    }

    updateExistingMatchCard(card, selectorName, matchData) {
        const currentHomeScore = matchData.home_score || 0;
        const currentAwayScore = matchData.away_score || 0;
        const previousHomeScore = parseInt(card.dataset.previousHomeScore) || 0;
        const previousAwayScore = parseInt(card.dataset.previousAwayScore) || 0;

        // Update stored scores
        card.dataset.previousHomeScore = currentHomeScore;
        card.dataset.previousAwayScore = currentAwayScore;

        // Update card class based on BTTS status
        const newClass = this.getMatchCardClass(matchData);
        const currentClass = card.className.replace('match-card', '').trim();

        if (newClass !== currentClass) {
            card.className = `match-card ${newClass}`;
        }

        // Update BTTS status
        const bttsStatus = this.getBTTSStatusInfo(matchData);
        const bttsStatusElement = card.querySelector('.btts-status');
        if (bttsStatusElement) {
            const currentBttsClass = bttsStatusElement.className.replace('btts-status', '').trim();
            const newBttsClass = `btts-status ${bttsStatus.class}`;

            if (newBttsClass !== currentBttsClass) {
                bttsStatusElement.className = newBttsClass;
                bttsStatusElement.dataset.bttsStatus = bttsStatus.key;
            }

            // Update BTTS text and icon
            const bttsIcon = bttsStatusElement.querySelector('.btts-icon');
            const bttsText = bttsStatusElement.childNodes[bttsStatusElement.childNodes.length - 1];

            if (bttsIcon) bttsIcon.textContent = bttsStatus.icon;
            if (bttsText) bttsText.textContent = ` ${bttsStatus.text}`;
        }

        // Update match status
        const matchStatus = this.getMatchStatus(matchData);
        const matchStatusElement = card.querySelector('.match-status');
        if (matchStatusElement) {
            matchStatusElement.className = `match-status ${matchStatus.class}`;
            matchStatusElement.textContent = matchStatus.text;
        }

        // Update score
        const scoreElement = card.querySelector('.score');
        if (scoreElement) {
            const newScoreLine = this.formatScoreLine(matchData);
            if (scoreElement.textContent !== newScoreLine) {
                scoreElement.textContent = newScoreLine;
                scoreElement.classList.add('score-updated');
                setTimeout(() => scoreElement.classList.remove('score-updated'), 1000);
            }
        }

        // Update time
        const timeElement = card.querySelector('.time');
        if (timeElement) {
            const newTime = this.getEnhancedMatchTime(matchData);
            if (timeElement.textContent !== newTime) {
                timeElement.textContent = newTime;
                timeElement.classList.add('time-updated');
                setTimeout(() => timeElement.classList.remove('time-updated'), 1000);
            }
        }
    }

    createMatchCard(selectorName, matchData) {
        const card = document.createElement('div');
        card.className = `match-card ${this.getMatchCardClass(matchData)}`;
        card.id = `match-${selectorName}`;

        const bttsStatus = this.getBTTSStatusInfo(matchData);
        const matchStatus = this.getMatchStatus(matchData);
        const scoreLine = this.formatScoreLine(matchData);
        const matchTime = this.getEnhancedMatchTime(matchData);

        let teamsContent = '';
        let leagueText = matchData.league || 'Unknown League';
        let scoreText = scoreLine;
        let timeText = matchTime;

        if (matchData.placeholder) {
            teamsContent = `<div class="team-names">${matchData.placeholder_text || 'Awaiting Match Assignment'}</div>`;
            leagueText = '—';
            scoreText = '—';
            timeText = '—';
        } else {
            const matchName = matchData.league ? `<div class="match-name">${matchData.league}</div>` : '';
            const teamNames = `<div class="team-names">${matchData.home_team || 'TBD'} vs ${matchData.away_team || 'TBD'}</div>`;
            teamsContent = matchName + teamNames;
        }

        card.innerHTML = `
            <div class="selector-name">${selectorName}</div>
            <div class="league-badge">${leagueText}</div>
            <div class="teams">${teamsContent}</div>
            <div class="score-display">
                <div class="score">${scoreText}</div>
                <div class="time">${timeText}</div>
            </div>
            <div class="btts-status ${bttsStatus.class}">
                ${bttsStatus.text}
            </div>
            <div class="match-status ${matchStatus.class}">
                ${matchStatus.text}
            </div>
        `;

        // Store current state for comparison
        card.dataset.previousHomeScore = matchData.home_score || 0;
        card.dataset.previousAwayScore = matchData.away_score || 0;
        card.dataset.bttsDetected = matchData.btts_detected || false;

        // Add enhanced click handler for match details
        card.addEventListener('click', (e) => {
            // Add click animation
            card.style.transform = 'scale(1.05)';
            setTimeout(() => {
                card.style.transform = '';
            }, 200);

            this.showMatchDetails(selectorName, matchData);
        });

        // Add hover effects
        card.addEventListener('mouseenter', () => {
            if (!card.classList.contains('btts-highlight')) {
                card.style.transform = 'translateY(-3px) scale(1.02)';
                card.style.transition = 'all 0.3s ease';
            }
        });

        card.addEventListener('mouseleave', () => {
            if (!card.classList.contains('btts-highlight')) {
                card.style.transform = '';
            }
        });

        return card;
    }

    getMatchCardClass(matchData) {
        if (matchData.placeholder) {
            return 'btts-pending placeholder';
        } else if (matchData.btts_detected) {
            return 'btts-success';
        } else if (matchData.status === 'finished') {
            return 'btts-failed';
        } else {
            return 'btts-pending';
        }
    }

    getBTTSStatusInfo(matchData) {
        if (matchData.placeholder) {
            return {
                class: 'pending',
                text: 'AWAITING ASSIGNMENT',
                icon: '⏳',
                key: 'placeholder'
            };
        } else if (matchData.btts_detected) {
            return {
                class: 'success',
                text: 'BOTH SCORED',
                icon: '🎯',
                key: 'success'
            };
        } else if (matchData.status === 'finished') {
            return {
                class: 'failed',
                text: 'NO BTTS',
                icon: '❌',
                key: 'failed'
            };
        } else if (matchData.status === 'live') {
            const homeScore = matchData.home_score || 0;
            const awayScore = matchData.away_score || 0;

            if (homeScore > 0 && awayScore > 0) {
                return {
                    class: 'success',
                    text: 'BTTS LIVE!',
                    icon: '⚡',
                    key: 'live-btts'
                };
            } else if (homeScore > 0 || awayScore > 0) {
                return {
                    class: 'pending',
                    text: 'ONE SCORED',
                    icon: '⏳',
                    key: 'one-scored'
                };
            } else {
                return {
                    class: 'pending',
                    text: 'AWAITING GOALS',
                    icon: '🕐',
                    key: 'awaiting'
                };
            }
        } else {
            return {
                class: 'pending',
                text: 'NOT STARTED',
                icon: '⏰',
                key: 'not-started'
            };
        }
    }

    getMatchStatus(matchData) {
        const status = matchData.status;
        if (status === 'no_selection') {
            return { class: 'pending', text: 'AWAITING SELECTION' };
        } else if (status === 'not_started') {
            return { class: 'pending', text: 'NOT STARTED' };
        } else if (status === 'finished') {
            return { class: 'finished', text: 'FINISHED' };
        } else if (status === 'live' || status === 'first_half' || status === 'second_half') {
            return { class: 'live', text: 'LIVE' };
        } else {
            return { class: 'pending', text: status.toUpperCase() };
        }
    }

    getEnhancedMatchTime(matchData) {
        const status = matchData.status;

        if (status === 'not_started') {
            return 'Not Started';
        } else if (status === 'finished') {
            return 'FT';
        } else if (status === 'live') {
            // Enhanced live timing with more detailed information
            const matchTime = matchData.match_time || matchData.minute || 'LIVE';
            if (typeof matchTime === 'number') {
                return `LIVE ${matchTime}'`;
            }
            return matchTime;
        } else if (status === 'first_half') {
            const matchTime = matchData.match_time || matchData.minute || 'LIVE';
            const timeStr = typeof matchTime === 'number' ? `${matchTime}'` : matchTime;
            return `1H ${timeStr}`;
        } else if (status === 'second_half') {
            const matchTime = matchData.match_time || matchData.minute || 'LIVE';
            const timeStr = typeof matchTime === 'number' ? `${matchTime}'` : matchTime;
            return `2H ${timeStr}`;
        } else if (status === 'half_time') {
            return 'HT';
        } else if (status === 'extra_time') {
            return 'ET';
        } else if (status === 'penalties') {
            return 'PEN';
        } else {
            return status.replace('_', ' ').toUpperCase();
        }
    }

    formatScoreLine(matchData) {
        const homeScore = matchData.home_score || 0;
        const awayScore = matchData.away_score || 0;

        // Enhanced score formatting with better visual presentation
        let scoreLine = `${homeScore}-${awayScore}`;

        // Add plus indicators for recent goals with enhanced styling
        if (matchData.recent_goals && matchData.recent_goals.length > 0) {
            const recentGoals = matchData.recent_goals.slice(-2); // Show last 2 goals
            const indicators = recentGoals.map(goal => {
                if (goal === 'home') return '+';
                if (goal === 'away') return '+';
                return '';
            }).join('');

            if (indicators) {
                scoreLine += ` ${indicators}`;
            }
        }

        // Add status indicators for better context
        if (matchData.status === 'live') {
            const minute = matchData.match_time || matchData.minute;
            if (typeof minute === 'number' && minute > 0) {
                scoreLine += ` (${minute}')`;
            }
        }

        return scoreLine;
    }

    showMatchDetails(selectorName, matchData) {
        // Future enhancement: show detailed match information
        console.log('Match details for:', selectorName, matchData);

        // For now, just show a simple alert
        const status = matchData.btts_detected ? 'BTTS SUCCESS' : 'BTTS PENDING';
        const scoreLine = `${matchData.home_score || 0}-${matchData.away_score || 0}`;
        alert(`${selectorName}: ${status}\nScore: ${scoreLine}\nTeams: ${matchData.home_team} vs ${matchData.away_team}`);
    }

    triggerCelebration() {
        // Add celebration animation to successful matches
        const successCards = document.querySelectorAll('.match-card.btts-success');
        successCards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('celebrating');
                card.style.transform = 'scale(1.05)';
                card.style.boxShadow = '0 8px 32px rgba(40, 167, 69, 0.3)';

                setTimeout(() => {
                    card.classList.remove('celebrating');
                    card.style.transform = 'scale(1)';
                    card.style.boxShadow = '';
                }, 2000);
            }, index * 200);
        });

        // Trigger enhanced confetti effect
        this.triggerConfetti();

        // Add sound notification if available (optional enhancement)
        this.playNotificationSound();
    }

    triggerConfetti() {
        // Try multiple confetti libraries
        if (window.confetti) {
            // Canvas confetti
            window.confetti({
                particleCount: 150,
                spread: 80,
                origin: { y: 0.6 },
                colors: ['#28a745', '#20c997', '#17a2b8', '#ffc107'],
                gravity: 0.8,
                drift: 0.5
            });
        } else if (typeof Party !== 'undefined' && Party.default) {
            // Party.js confetti
            new Party.default(document.body).party();
        } else {
            // Fallback: Create simple CSS-based celebration
            this.createCSSCelebration();
        }
    }

    createCSSCelebration() {
        // Create floating celebration elements
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                const celebration = document.createElement('div');
                celebration.innerHTML = '🎉';
                celebration.style.cssText = `
                    position: fixed;
                    top: 20%;
                    left: ${Math.random() * 100}%;
                    font-size: 2rem;
                    pointer-events: none;
                    z-index: 1000;
                    animation: floatUp 3s ease-out forwards;
                `;

                document.body.appendChild(celebration);

                setTimeout(() => {
                    celebration.remove();
                }, 3000);
            }, i * 100);
        }

        // Add CSS animation if not exists
        if (!document.querySelector('#celebration-styles')) {
            const style = document.createElement('style');
            style.id = 'celebration-styles';
            style.textContent = `
                @keyframes floatUp {
                    0% {
                        transform: translateY(0) rotate(0deg);
                        opacity: 1;
                    }
                    100% {
                        transform: translateY(-100vh) rotate(360deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    playNotificationSound() {
        // Optional: Play a subtle notification sound
        // This would require audio files to be available
        try {
            // Create a simple beep using Web Audio API
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (e) {
            // Silently fail if Web Audio API is not available
            console.log('Audio notification not available');
        }
    }

    handleError(error) {
        this.retryCount++;
        console.error(`❌ Error ${this.retryCount}/${this.maxRetries}:`, error);

        if (this.retryCount >= this.maxRetries) {
            this.showError(error);
        } else {
            this.updateConnectionStatus(false);

            // Retry after interval
            setTimeout(() => {
                this.fetchData();
            }, this.retryInterval);
        }
    }

    showLoading() {
        this.loadingState.style.display = 'block';
        this.errorState.style.display = 'none';
        this.matchesContainer.style.display = 'none';
    }

    hideLoading() {
        this.loadingState.style.display = 'none';
        this.matchesContainer.style.display = 'grid';
    }

    showError(error) {
        this.loadingState.style.display = 'none';
        this.matchesContainer.style.display = 'none';
        this.errorState.style.display = 'block';

        // Update error message if available
        const errorMessage = this.errorState.querySelector('p');
        if (errorMessage && error.message) {
            errorMessage.textContent = `Error: ${error.message}. Please check your connection and try again.`;
        }
    }

    hideError() {
        this.errorState.style.display = 'none';
    }

    handleNoSelections(data) {
        // Handle case when no selections have been made yet
        this.updateConnectionStatus(true);

        // Update accumulator summary for no selections state
        this.accumulatorStatus.innerHTML = `
            <span class="status-badge pending">
                AWAITING SELECTIONS
            </span>
        `;

        // Reset statistics
        this.bttsSuccessCount.textContent = '0';
        this.bttsPendingCount.textContent = '0';
        this.bttsFailedCount.textContent = '0';

        // Show no selections message
        this.showNoSelections();

        // Hide loading/error states
        this.hideLoading();
        this.hideError();

        console.log('ℹ️ No selections found - showing awaiting selections state');
    }

    showNoSelections() {
        this.matchesContainer.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                <div style="font-size: 4rem; margin-bottom: 20px;">⚽</div>
                <h3>Awaiting Match Selections</h3>
                <p style="color: #6c757d; margin-bottom: 20px;">
                    No matches have been selected yet for this week's BTTS accumulator.
                </p>
                <div style="background: rgba(255, 255, 255, 0.8); border-radius: 10px; padding: 20px; margin: 20px 0; border: 2px solid rgba(23, 162, 184, 0.2);">
                    <h4 style="margin-top: 0; color: #17a2b8;">How to get started:</h4>
                    <ol style="text-align: left; max-width: 400px; margin: 0 auto; color: #495057;">
                        <li>Visit the <strong>Admin Interface</strong> to select matches</li>
                        <li>Assign <strong>8 matches</strong> to different selectors</li>
                        <li>Return here to <strong>track live BTTS results</strong></li>
                    </ol>
                </div>
                <div style="margin-top: 20px;">
                    <a href="/admin" style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 25px; font-weight: 600; display: inline-block; transition: all 0.3s ease;">
                        Go to Admin Interface →
                    </a>
                </div>
            </div>
        `;
    }

    showNoMatches() {
        this.matchesContainer.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <div style="font-size: 3rem; margin-bottom: 20px;">📭</div>
                <h3>No Matches Found</h3>
                <p>No matches are currently being tracked. Please check back later.</p>
            </div>
        `;
    }

    updateConnectionStatus(connected) {
        const statusDot = this.connectionStatus.querySelector('.status-dot');
        const statusText = this.connectionStatus.querySelector('.status-text');

        if (connected === 'loading') {
            statusDot.className = 'status-dot';
            statusText.textContent = 'Loading...';
        } else if (connected === 'test') {
            statusDot.className = 'status-dot connected';
            statusText.textContent = 'Connected';
            this.isConnected = true;
        } else if (connected) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = 'Connected';
            this.isConnected = true;
        } else {
            statusDot.className = 'status-dot disconnected';
            statusText.textContent = 'Disconnected';
            this.isConnected = false;
        }
    }

    // Public method to manually refresh data
    refresh() {
        this.retryCount = 0;
        this.fetchData();
    }

    // Public method to get current data
    getCurrentData() {
        return this.currentData;
    }

    // Public method to check connection status
    isConnected() {
        return this.isConnected;
    }

    // Cleanup method
    destroy() {
        this.pauseUpdates();

        // Remove event listeners
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('online', this.handleOnline);
        window.removeEventListener('offline', this.handleOffline);
    }
}

// Initialize tracker when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bttsTracker = new BTTSTracker();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BTTSTracker;
}