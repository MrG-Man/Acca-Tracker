// Mockup Page - Enhanced Interactive Features

class MockupCelebration {
    constructor() {
        this.particles = [];
        this.messages = [
            "⚽ BTTS SUCCESS! ⚽",
            "💰 Great Progress! 💰",
            "🎯 Good BTTS Tracking! 🎯",
            "🏆 Accumulator In Play! 🏆",
            "⚡ Live Updates Active! ⚡"
        ];
        this.messageIndex = 0;
        this.init();
    }

    init() {
        this.createParticles();
        this.startCelebrationMessages();
        this.addInteractiveEffects();
        this.startAmbientAnimations();
    }

    createParticles() {
        const container = document.querySelector('.celebration-overlay');
        if (!container) return;

        // Create floating particles
        for (let i = 0; i < 30; i++) {
            setTimeout(() => {
                this.createParticle(container);
            }, i * 200);
        }
    }

    createParticle(container) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.animationDuration = (Math.random() * 3 + 4) + 's';

        container.appendChild(particle);

        // Remove particle after animation
        setTimeout(() => {
            particle.remove();
        }, 9000);
    }

    startCelebrationMessages() {
        // Show floating messages periodically
        setInterval(() => {
            this.showFloatingMessage();
        }, 4000);
    }

    showFloatingMessage() {
        const message = document.createElement('div');
        message.className = 'floating-message';
        message.textContent = this.messages[this.messageIndex];

        document.body.appendChild(message);

        this.messageIndex = (this.messageIndex + 1) % this.messages.length;

        // Remove message after animation
        setTimeout(() => {
            message.remove();
        }, 4000);
    }

    addInteractiveEffects() {
        // Add click effects to match cards
        document.querySelectorAll('.match-card').forEach((card, index) => {
            card.addEventListener('click', () => {
                this.createSuccessBurst(card);
                this.triggerCardCelebration(card, index);
            });

            // Add hover effects
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px) scale(1.02)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });

        // Add click effect to accumulator summary
        const summaryCard = document.querySelector('.perfect-accumulator');
        if (summaryCard) {
            summaryCard.addEventListener('click', () => {
                this.celebrateAccumulator();
            });
        }
    }

    createSuccessBurst(card) {
        const burst = document.createElement('div');
        burst.className = 'success-burst';
        card.appendChild(burst);

        setTimeout(() => {
            burst.remove();
        }, 2000);
    }

    triggerCardCelebration(card, index) {
        // Add temporary celebration class
        card.classList.add('btts-highlight');

        // Create ripple effect
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: ripple 1s ease-out forwards;
            pointer-events: none;
            z-index: 10;
        `;

        card.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
            card.classList.remove('btts-highlight');
        }, 1000);
    }

    celebrateAccumulator() {
        // Special celebration for the accumulator
        const accumulator = document.querySelector('.perfect-accumulator');
        accumulator.style.animation = 'none';
        accumulator.style.transform = 'scale(1.05)';

        setTimeout(() => {
            accumulator.style.animation = 'perfectPulse 2s ease-in-out infinite';
            accumulator.style.transform = '';
        }, 500);

        // Trigger massive confetti
        this.createMassiveConfetti();
    }

    createMassiveConfetti() {
        const container = document.querySelector('.celebration-overlay');
        if (!container) return;

        for (let i = 0; i < 100; i++) {
            setTimeout(() => {
                const piece = document.createElement('div');
                piece.style.cssText = `
                    position: absolute;
                    width: 12px;
                    height: 12px;
                    background: ${['#28a745', '#20c997', '#17a2b8', '#ffc107'][Math.floor(Math.random() * 4)]};
                    left: ${Math.random() * 100}%;
                    top: -20px;
                    border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
                    animation: massiveFall 4s linear forwards;
                    box-shadow: 0 0 10px rgba(255,255,255,0.3);
                    z-index: 9999;
                `;

                container.appendChild(piece);

                setTimeout(() => piece.remove(), 4000);
            }, i * 20);
        }
    }

    startAmbientAnimations() {
        // Animate statistics periodically
        setInterval(() => {
            this.animateStatistics();
        }, 3000);
    }

    animateStatistics() {
        const statValues = document.querySelectorAll('.stat-value');

        statValues.forEach((stat, index) => {
            setTimeout(() => {
                stat.style.transform = 'scale(1.1)';
                stat.style.transition = 'transform 0.3s ease';

                setTimeout(() => {
                    stat.style.transform = '';
                }, 300);
            }, index * 100);
        });
    }
}

// Ripple animation CSS
const rippleCSS = `
@keyframes ripple {
    0% {
        width: 0;
        height: 0;
        opacity: 1;
        box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.8);
    }
    100% {
        width: 200px;
        height: 200px;
        opacity: 0;
        box-shadow: 0 0 0 100px rgba(40, 167, 69, 0.2);
    }
}
`;

// Massive fall animation CSS
const massiveFallCSS = `
@keyframes massiveFall {
    0% {
        transform: translateY(-20px) rotate(0deg);
        opacity: 1;
    }
    100% {
        transform: translateY(100vh) rotate(720deg);
        opacity: 0;
    }
}
`;

// Add CSS animations to document
function addAnimationStyles() {
    const style = document.createElement('style');
    style.textContent = rippleCSS + massiveFallCSS;
    document.head.appendChild(style);
}

// Sound effects simulation (visual feedback)
class SoundEffectSimulator {
    static trigger(soundType) {
        switch(soundType) {
            case 'success':
                this.createVisualBell();
                break;
            case 'goal':
                this.createGoalFlash();
                break;
            case 'perfect':
                this.createMassiveBell();
                break;
        }
    }

    static createVisualBell() {
        const bell = document.createElement('div');
        bell.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background: radial-gradient(circle, #ffc107, #fd7e14);
            border-radius: 50%;
            z-index: 10000;
            animation: bellRing 1s ease-in-out;
            box-shadow: 0 0 20px rgba(255, 193, 7, 0.6);
        `;

        document.body.appendChild(bell);

        setTimeout(() => bell.remove(), 1000);
    }

    static createGoalFlash() {
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(40, 167, 69, 0.3) 0%, transparent 70%);
            pointer-events: none;
            z-index: 9997;
            animation: goalFlash 0.5s ease-out;
        `;

        document.body.appendChild(flash);

        setTimeout(() => flash.remove(), 500);
    }

    static createMassiveBell() {
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                this.createVisualBell();
            }, i * 200);
        }
    }
}

// Statistics animation
class StatisticsAnimator {
    constructor() {
        this.stats = [
            { selector: '#btts-success-count', target: 5 },
            { selector: '#btts-pending-count', target: 2 },
            { selector: '#btts-failed-count', target: 1 }
        ];
        this.init();
    }

    init() {
        // Animate statistics on page load
        setTimeout(() => {
            this.animateStats();
        }, 1000);
    }

    animateStats() {
        this.stats.forEach((stat, index) => {
            setTimeout(() => {
                this.countUp(stat.selector, stat.target);
            }, index * 500);
        });
    }

    countUp(selector, target) {
        const element = document.querySelector(selector);
        if (!element) return;

        let current = 0;
        const increment = target / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
                // Trigger success sound when reaching target
                if (selector === '#btts-success-count') {
                    SoundEffectSimulator.trigger('perfect');
                }
            }
            element.textContent = Math.floor(current);
        }, 50);
    }
}

// Time display updater
class TimeUpdater {
    constructor() {
        this.updateInterval = null;
        this.init();
    }

    init() {
        this.updateTime();
        this.updateInterval = setInterval(() => {
            this.updateTime();
        }, 1000);
    }

    updateTime() {
        const timeElement = document.querySelector('#last-updated');
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString();
        }
    }
}

// Performance metrics display
class PerformanceMetrics {
    constructor() {
        this.metrics = {
            'Success Rate': '62%',
            'Total Selections': '8',
            'BTTS Achieved': '5',
            'Potential Returns': '£125.00',
            'System Status': 'In Progress'
        };
        this.init();
    }

    init() {
        // Performance indicators removed
    }

}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add animation styles
    addAnimationStyles();

    // Initialize celebration system
    const celebration = new MockupCelebration();

    // Initialize statistics animation
    const statsAnimator = new StatisticsAnimator();

    // Initialize time updater
    const timeUpdater = new TimeUpdater();

    // Initialize performance metrics
    const performanceMetrics = new PerformanceMetrics();

    // Add keyboard shortcuts for testing
    document.addEventListener('keydown', function(e) {
        switch(e.key) {
            case 'c':
                celebration.createMassiveConfetti();
                break;
            case 'm':
                celebration.showFloatingMessage();
                break;
            case 's':
                SoundEffectSimulator.trigger('success');
                break;
            case 'p':
                celebration.celebrateAccumulator();
                break;
        }
    });

    // Add subtle parallax effect to background elements
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const rate = scrolled * -0.5;

        document.querySelectorAll('.celebration-overlay').forEach(overlay => {
            overlay.style.transform = `translateY(${rate}px)`;
        });
    });

    console.log('🎯 Mockup page initialized with enhanced celebrations!');
    console.log('💡 Try pressing C for confetti, M for messages, S for sounds, P for perfect celebration!');
});