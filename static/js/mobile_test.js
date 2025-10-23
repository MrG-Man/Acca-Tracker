// Mobile Device Test Suite JavaScript
// Comprehensive mobile device simulation and testing functionality

class MobileDeviceTest {
    constructor() {
        this.currentMode = 'admin'; // 'admin' or 'tracker'
        this.currentOrientation = 'portrait'; // 'portrait' or 'landscape'
        this.devices = [
            'iphone-12',
            'iphone-se',
            'samsung-galaxy',
            'ipad'
        ];
        this.deviceConfigs = {
            'iphone-12': {
                width: 390,
                height: 844,
                url: '/admin',
                name: 'iPhone 12 Pro'
            },
            'iphone-se': {
                width: 375,
                height: 667,
                url: '/admin',
                name: 'iPhone SE'
            },
            'samsung-galaxy': {
                width: 360,
                height: 800,
                url: '/admin',
                name: 'Samsung Galaxy S21'
            },
            'ipad': {
                width: 768,
                height: 1024,
                url: '/admin',
                name: 'iPad'
            }
        };
        this.loadTimes = {};
        this.startTime = Date.now();

        this.init();
    }

    init() {
        // Initialize all devices
        this.initializeDevices();

        // Set up event listeners
        this.setupEventListeners();

        // Start monitoring
        this.startMonitoring();

        // Update device info display
        this.updateDeviceInfo();

        console.log('Mobile Device Test Suite initialized');
    }

    initializeDevices() {
        this.devices.forEach(device => {
            const iframe = document.getElementById(`${device}-iframe`);
            const loading = document.getElementById(`${device}-loading`);
            const status = document.getElementById(`${device}-status`);

            if (iframe && loading) {
                // Show loading state
                loading.style.display = 'flex';

                // Set initial URL based on current mode
                const config = this.deviceConfigs[device];
                iframe.src = config.url;

                // Set up iframe load handler
                iframe.addEventListener('load', () => {
                    this.handleIframeLoad(device);
                });

                // Set up iframe error handler
                iframe.addEventListener('error', () => {
                    this.handleIframeError(device);
                });

                console.log(`Initialized ${device}`);
            }
        });
    }

    setupEventListeners() {
        // Global functions for buttons
        window.switchMode = (mode) => this.switchMode(mode);
        window.setOrientation = (orientation) => this.setOrientation(orientation);
        window.refreshAllDevices = () => this.refreshAllDevices();
        window.testConnectivity = () => this.testConnectivity();
        window.toggleFullscreen = (device) => this.toggleFullscreen(device);
        window.handleIframeLoad = (device) => this.handleIframeLoad(device);
        window.handleIframeError = (device) => this.handleIframeError(device);
    }

    switchMode(mode) {
        if (mode !== 'admin' && mode !== 'tracker') {
            console.error('Invalid mode:', mode);
            return;
        }

        this.currentMode = mode;

        // Update button states
        const adminBtn = document.querySelector('.device-btn[data-mode="admin"]');
        const trackerBtn = document.querySelector('.device-btn[data-mode="tracker"]');

        if (mode === 'admin') {
            adminBtn.classList.add('active');
            trackerBtn.classList.remove('active');
        } else {
            trackerBtn.classList.add('active');
            adminBtn.classList.remove('active');
        }

        // Update all device URLs
        this.devices.forEach(device => {
            const config = this.deviceConfigs[device];
            const newUrl = mode === 'admin' ? '/admin' : '/btts-tracker';

            // Update config
            config.url = newUrl;

            // Update iframe
            const iframe = document.getElementById(`${device}-iframe`);
            if (iframe) {
                // Show loading
                const loading = document.getElementById(`${device}-loading`);
                if (loading) loading.style.display = 'flex';

                // Update src
                iframe.src = newUrl;
            }
        });

        // Update device info
        this.updateDeviceInfo();

        console.log(`Switched to ${mode} mode`);
    }

    setOrientation(orientation) {
        if (orientation !== 'portrait' && orientation !== 'landscape') {
            console.error('Invalid orientation:', orientation);
            return;
        }

        this.currentOrientation = orientation;

        // Update button states
        const portraitBtn = document.querySelector('.orientation-btn[onclick*="portrait"]');
        const landscapeBtn = document.querySelector('.orientation-btn[onclick*="landscape"]');

        if (orientation === 'portrait') {
            portraitBtn.classList.add('active');
            landscapeBtn.classList.remove('active');
        } else {
            landscapeBtn.classList.add('active');
            portraitBtn.classList.remove('active');
        }

        // Apply orientation to devices (visual rotation)
        this.devices.forEach(device => {
            const frame = document.querySelector(`.device-frame[data-device="${device}"]`);
            if (frame) {
                if (orientation === 'landscape') {
                    frame.style.transform = 'rotate(90deg)';
                    // Adjust for landscape rotation
                    const screen = frame.querySelector('.device-screen');
                    if (screen) {
                        screen.style.transform = 'rotate(-90deg)';
                    }
                } else {
                    frame.style.transform = 'rotate(0deg)';
                    const screen = frame.querySelector('.device-screen');
                    if (screen) {
                        screen.style.transform = 'rotate(0deg)';
                    }
                }
            }
        });

        // Update device info
        this.updateDeviceInfo();

        console.log(`Set orientation to ${orientation}`);
    }

    handleIframeLoad(device) {
        const iframe = document.getElementById(`${device}-iframe`);
        const loading = document.getElementById(`${device}-loading`);
        const status = document.getElementById(`${device}-status`);

        if (loading) loading.style.display = 'none';
        if (iframe) {
            iframe.classList.add('loaded');
            // Record load time
            this.loadTimes[device] = Date.now() - this.startTime;
        }
        if (status) {
            status.classList.remove('error');
        }

        console.log(`${device} iframe loaded successfully`);
        this.updatePerformanceInfo();
    }

    handleIframeError(device) {
        const loading = document.getElementById(`${device}-loading`);
        const status = document.getElementById(`${device}-status`);
        const screen = document.getElementById(`${device}-screen`);

        if (loading) loading.style.display = 'none';
        if (status) {
            status.classList.add('error');
        }
        if (screen) {
            screen.innerHTML = `
                <div class="device-error">
                    <p>Failed to load content</p>
                    <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; border: none; border-radius: 5px; background: #dc3545; color: white; cursor: pointer;">
                        Retry
                    </button>
                </div>
            `;
        }

        console.error(`${device} iframe failed to load`);
        this.updatePerformanceInfo();
    }

    refreshAllDevices() {
        this.startTime = Date.now();
        this.loadTimes = {};

        this.devices.forEach(device => {
            const iframe = document.getElementById(`${device}-iframe`);
            const loading = document.getElementById(`${device}-loading`);
            const status = document.getElementById(`${device}-status`);

            if (loading) loading.style.display = 'flex';
            if (status) status.classList.remove('error');

            if (iframe) {
                const config = this.deviceConfigs[device];
                iframe.src = config.url;
            }
        });

        console.log('Refreshed all devices');
    }

    async testConnectivity() {
        const devices = ['iphone-12', 'iphone-se', 'samsung-galaxy', 'ipad'];
        const results = {};

        for (const device of devices) {
            try {
                const config = this.deviceConfigs[device];
                const response = await fetch(config.url, {
                    method: 'HEAD',
                    mode: 'no-cors'
                });
                results[device] = 'connected';
            } catch (error) {
                results[device] = 'error';
                console.error(`Connectivity test failed for ${device}:`, error);
            }
        }

        // Update status indicators
        Object.keys(results).forEach(device => {
            const status = document.getElementById(`${device}-status`);
            if (status) {
                status.classList.remove('error');
                if (results[device] === 'error') {
                    status.classList.add('error');
                }
            }
        });

        // Show results
        const connected = Object.values(results).filter(r => r === 'connected').length;
        const total = Object.keys(results).length;

        alert(`Connectivity Test Results:\n\nConnected: ${connected}/${total}\n${connected === total ? '✅ All devices connected!' : '⚠️ Some devices failed'}`);

        console.log('Connectivity test results:', results);
    }

    toggleFullscreen(device) {
        const frame = document.querySelector(`.device-frame[data-device="${device}"]`);
        if (!frame) return;

        if (!document.fullscreenElement) {
            frame.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen for ${device}:`, err);
            });
        } else {
            document.exitFullscreen();
        }
    }

    startMonitoring() {
        // Monitor iframe status every 5 seconds
        setInterval(() => {
            this.devices.forEach(device => {
                const iframe = document.getElementById(`${device}-iframe`);
                if (iframe && iframe.contentWindow) {
                    try {
                        // Try to access iframe content to check if it's responsive
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (iframeDoc) {
                            // Update status indicator
                            const status = document.getElementById(`${device}-status`);
                            if (status && status.classList.contains('error')) {
                                // Try to reload if there was an error
                                console.log(`Attempting to reload ${device} due to error state`);
                            }
                        }
                    } catch (error) {
                        // Cross-origin error is expected, just log it
                        console.debug(`Cross-origin access denied for ${device} (expected)`);
                    }
                }
            });
        }, 5000);

        // Update performance info every 2 seconds
        setInterval(() => {
            this.updatePerformanceInfo();
        }, 2000);
    }

    updateDeviceInfo() {
        const modeSpan = document.getElementById('current-mode');
        const orientationSpan = document.getElementById('current-orientation');
        const devicesSpan = document.getElementById('active-devices');

        if (modeSpan) modeSpan.textContent = this.currentMode;
        if (orientationSpan) orientationSpan.textContent = this.currentOrientation;
        if (devicesSpan) devicesSpan.textContent = this.devices.length;
    }

    updatePerformanceInfo() {
        const avgLoadTimeSpan = document.getElementById('avg-load-time');
        const lastUpdateSpan = document.getElementById('last-update');
        const overallStatusSpan = document.getElementById('overall-status');

        // Calculate average load time
        const loadTimes = Object.values(this.loadTimes).filter(time => time > 0);
        if (loadTimes.length > 0) {
            const avgTime = loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length;
            if (avgLoadTimeSpan) avgLoadTimeSpan.textContent = `${Math.round(avgTime)}ms`;
        }

        // Update last update time
        if (lastUpdateSpan) {
            lastUpdateSpan.textContent = new Date().toLocaleTimeString();
        }

        // Check overall status
        const errorStatuses = this.devices.filter(device => {
            const status = document.getElementById(`${device}-status`);
            return status && status.classList.contains('error');
        });

        if (overallStatusSpan) {
            if (errorStatuses.length === 0) {
                overallStatusSpan.textContent = '● Active';
                overallStatusSpan.style.color = '#28a745';
            } else if (errorStatuses.length < this.devices.length) {
                overallStatusSpan.textContent = `● Partial (${this.devices.length - errorStatuses.length}/${this.devices.length})`;
                overallStatusSpan.style.color = '#ffc107';
            } else {
                overallStatusSpan.textContent = '● Error';
                overallStatusSpan.style.color = '#dc3545';
            }
        }
    }

    // Public API methods
    getCurrentMode() {
        return this.currentMode;
    }

    getCurrentOrientation() {
        return this.currentOrientation;
    }

    getDeviceInfo(device) {
        return this.deviceConfigs[device] || null;
    }

    getAllDevices() {
        return [...this.devices];
    }

    getLoadTimes() {
        return {...this.loadTimes};
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileDeviceTest = new MobileDeviceTest();
});

// Handle fullscreen change events
document.addEventListener('fullscreenchange', () => {
    const fullscreenBtn = document.querySelector('.fullscreen-btn:-webkit-full-screen');
    if (fullscreenBtn) {
        fullscreenBtn.textContent = document.fullscreenElement ? '⛶' : '⛶';
    }
});

// Handle visibility change (pause/resume when tab is not visible)
document.addEventListener('visibilitychange', () => {
    if (window.mobileDeviceTest) {
        if (document.hidden) {
            console.log('Tab hidden - pausing monitoring');
        } else {
            console.log('Tab visible - resuming monitoring');
            // Refresh device info when tab becomes visible
            window.mobileDeviceTest.updateDeviceInfo();
            window.mobileDeviceTest.updatePerformanceInfo();
        }
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
            case 'r':
                e.preventDefault();
                window.mobileDeviceTest.refreshAllDevices();
                break;
            case 'a':
                e.preventDefault();
                window.mobileDeviceTest.switchMode('admin');
                break;
            case 't':
                e.preventDefault();
                window.mobileDeviceTest.switchMode('tracker');
                break;
            case 'p':
                e.preventDefault();
                window.mobileDeviceTest.setOrientation('portrait');
                break;
            case 'l':
                e.preventDefault();
                window.mobileDeviceTest.setOrientation('landscape');
                break;
        }
    }
});

// Export for use in other scripts if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileDeviceTest;
}