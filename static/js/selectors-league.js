/* Modern Selectors League JavaScript - Mobile-First Design */
// Handles league table display with card-based mobile layout

// Global state management
const AppState = {
    data: [],
    isLoading: false,
    error: null,
    lastUpdate: null,
    debugMode: false
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    try {
        // Initialize debug mode
        setupDebugToggle();
        
        // Load initial data
        await loadLeagueData();
        
        // Setup periodic refresh
        setupAutoRefresh();
        
        // Add touch/swipe gestures for mobile
        setupMobileGestures();
        
    } catch (error) {
        console.error('App initialization failed:', error);
        showToast('Failed to initialize app', 'error');
    }
}

/* ===== Data Loading ===== */
async function loadLeagueData() {
    if (AppState.isLoading) return;
    
    try {
        setLoadingState(true);
        hideError();
        hideEmptyState();
        
        const response = await fetch('/api/selectors-league', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.data = data;
        AppState.lastUpdate = new Date();
        
        renderLeagueData(data);
        updateLastUpdateTime();
        
        setLoadingState(false);
        
        if (AppState.debugMode) {
            console.log('League data loaded:', data);
        }
        
    } catch (error) {
        console.error('Error loading league data:', error);
        AppState.error = error.message;
        setLoadingState(false);
        showError();
        showToast('Failed to load league data', 'error');
    }
}

function renderLeagueData(data) {
    if (!data.success || !data.selectors || data.selectors.length === 0) {
        showEmptyState();
        return;
    }
    
    // Sort selectors by points (descending)
    const sortedSelectors = data.selectors
        .sort((a, b) => b.total_points - a.total_points);
    
    const container = document.getElementById('leagueStandings');
    
    // Clear existing content
    container.innerHTML = '';
    
    // Render each selector as a card
    sortedSelectors.forEach((selector, index) => {
        const card = createLeagueCard(selector, index + 1);
        container.appendChild(card);
    });
    
    // Add animation delay for staggered entrance
    const cards = container.querySelectorAll('.league-card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('animate-in');
    });
}

/* ===== Card Creation ===== */
function createLeagueCard(selector, position) {
    const pointsClass = selector.total_points > 0 ? 'points-positive' :
                      selector.total_points === 0 ? 'points-zero' : 'points-negative';
    
    const positionClass = position === 1 ? 'position-1' :
                         position === 2 ? 'position-2' :
                         position === 3 ? 'position-3' : 'position-other';
    
    const card = document.createElement('div');
    card.className = 'league-card';
    card.setAttribute('data-selector-id', selector.selector_id || selector.id || position);
    
    // Enhanced selector info with additional stats if available
    const selections = selector.selections || selector.total_matches || 0;
    const correct = selector.correct_predictions || selector.btts_successes || 0;
    const accuracy = selections > 0 ? Math.round((correct / selections) * 100) : 0;
    
    card.innerHTML = `
        <div class="position-badge ${positionClass}">
            ${position}
        </div>
        
        <div class="selector-info">
            <div class="selector-name">${selector.selector_name || selector.name || 'Unknown'}</div>
            <div class="selector-stats">
                <span class="stat-item">
                    <span class="stat-icon">🎯</span>
                    <span class="stat-value">${accuracy}%</span>
                </span>
                <span class="stat-item">
                    <span class="stat-icon">✅</span>
                    <span class="stat-value">${correct}</span>
                </span>
                <span class="stat-item">
                    <span class="stat-icon">📊</span>
                    <span class="stat-value">${selections}</span>
                </span>
            </div>
        </div>
        
        <div class="points-display">
            <div class="points-value ${pointsClass}">${selector.total_points}</div>
            <div class="points-label">points</div>
        </div>
    `;
    
    // Add click handler for detailed view (mobile-friendly)
    card.addEventListener('click', () => {
        if (AppState.debugMode) {
            console.log('Card clicked:', selector);
        }
        showSelectorDetails(selector, position);
    });
    
    // Add touch feedback
    card.addEventListener('touchstart', function() {
        this.style.transform = 'scale(0.98)';
    });
    
    card.addEventListener('touchend', function() {
        this.style.transform = '';
    });
    
    return card;
}

/* ===== State Management ===== */
function setLoadingState(isLoading) {
    AppState.isLoading = isLoading;
    const loadingElement = document.getElementById('leagueLoading');
    
    if (isLoading) {
        loadingElement.classList.add('active');
    } else {
        loadingElement.classList.remove('active');
    }
}

function showError() {
    const errorElement = document.getElementById('errorState');
    errorElement.style.display = 'block';
}

function hideError() {
    const errorElement = document.getElementById('errorState');
    errorElement.style.display = 'none';
}

function showEmptyState() {
    const emptyElement = document.getElementById('emptyState');
    emptyElement.style.display = 'block';
}

function hideEmptyState() {
    const emptyElement = document.getElementById('emptyState');
    emptyElement.style.display = 'none';
}

/* ===== Interactive Features ===== */
function retryLoad() {
    hideError();
    loadLeagueData();
}

function updateLastUpdateTime() {
    const updateElement = document.getElementById('lastUpdateTime');
    if (updateElement && AppState.lastUpdate) {
        const timeString = AppState.lastUpdate.toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit'
        });
        updateElement.textContent = timeString;
    }
}

/* ===== Debug Features ===== */
function setupDebugToggle() {
    const debugToggle = document.getElementById('debugToggle');
    const debugCheckbox = document.getElementById('debugMode');
    
    // Show debug toggle in development or when URL has debug parameter
    const urlParams = new URLSearchParams(window.location.search);
    const isDebugMode = urlParams.has('debug') || localStorage.getItem('selectors-league-debug') === 'true';
    
    if (isDebugMode) {
        debugToggle.style.display = 'flex';
        AppState.debugMode = true;
        debugCheckbox.checked = true;
    }
    
    debugCheckbox.addEventListener('change', function() {
        AppState.debugMode = this.checked;
        localStorage.setItem('selectors-league-debug', this.checked);
        
        if (AppState.debugMode) {
            console.log('Debug mode enabled');
        } else {
            console.log('Debug mode disabled');
        }
    });
}

/* ===== Mobile Optimizations ===== */
function setupMobileGestures() {
    // Add pull-to-refresh functionality
    let startY = 0;
    let currentY = 0;
    let isRefreshing = false;
    
    const container = document.querySelector('.mobile-container');
    
    container.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
    });
    
    container.addEventListener('touchmove', function(e) {
        if (isRefreshing) return;
        
        currentY = e.touches[0].clientY;
        const deltaY = currentY - startY;
        
        // Only allow pull-to-refresh from top
        if (window.scrollY === 0 && deltaY > 50) {
            e.preventDefault();
            showPullToRefresh(deltaY);
        }
    });
    
    container.addEventListener('touchend', function() {
        if (isRefreshing) return;
        
        const deltaY = currentY - startY;
        if (deltaY > 100) {
            performPullToRefresh();
        }
        hidePullToRefresh();
    });
}

function showPullToRefresh(deltaY) {
    // Visual feedback for pull-to-refresh
    const header = document.querySelector('.mobile-header');
    header.style.transform = `translateY(${Math.min(deltaY - 50, 50)}px)`;
}

function hidePullToRefresh() {
    const header = document.querySelector('.mobile-header');
    header.style.transform = '';
}

async function performPullToRefresh() {
    showToast('Refreshing...', 'info');
    await loadLeagueData();
    showToast('Updated!', 'success');
}

/* ===== Auto Refresh ===== */
function setupAutoRefresh() {
    // Refresh every 5 minutes
    setInterval(async () => {
        if (!AppState.isLoading) {
            await loadLeagueData();
        }
    }, 5 * 60 * 1000);
}

/* ===== Modal/Detail Views ===== */
function showSelectorDetails(selector, position) {
    // Create a simple modal for selector details
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">${selector.selector_name}</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Position</span>
                        <span class="detail-value">#${position}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Total Points</span>
                        <span class="detail-value">${selector.total_points}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Selections</span>
                        <span class="detail-value">${selector.selections || 0}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Correct Predictions</span>
                        <span class="detail-value">${selector.correct_predictions || 0}</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
            </div>
        </div>
    `;
    
    // Add modal styles
    if (!document.getElementById('modal-styles')) {
        const styles = document.createElement('style');
        styles.id = 'modal-styles';
        styles.textContent = `
            .detail-grid {
                display: grid;
                gap: 1rem;
            }
            .detail-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                background: var(--card-bg);
                border-radius: 0.5rem;
                border: 1px solid var(--border-color);
            }
            .detail-label {
                color: var(--text-secondary);
                font-weight: 500;
            }
            .detail-value {
                color: var(--text-primary);
                font-weight: 600;
            }
        `;
        document.head.appendChild(styles);
    }
    
    document.body.appendChild(modal);
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

/* ===== Toast Notifications ===== */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/* ===== Animation Classes ===== */
const style = document.createElement('style');
style.textContent = `
    .animate-in {
        animation: slideInUp 0.3s ease-out forwards;
        opacity: 0;
        transform: translateY(20px);
    }
    
    @keyframes slideInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .league-card:active {
        transform: scale(0.98) !important;
    }
`;
document.head.appendChild(style);

/* ===== Error Recovery ===== */
window.addEventListener('online', function() {
    showToast('Connection restored', 'success');
    if (AppState.error) {
        loadLeagueData();
    }
});

window.addEventListener('offline', function() {
    showToast('No internet connection', 'error');
});

// Export functions for global access
window.retryLoad = retryLoad;
window.showToast = showToast;