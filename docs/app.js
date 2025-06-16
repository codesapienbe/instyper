// Instyper Website JavaScript

// Theme toggle functionality
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('theme-toggle');
        this.themeIcon = this.themeToggle.querySelector('.theme-toggle__icon');
        this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
        
        this.init();
    }
    
    init() {
        this.setTheme(this.currentTheme);
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)')
            .addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
    }
    
    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    
    getStoredTheme() {
        // Since we can't use localStorage, we'll rely on system preference
        return null;
    }
    
    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-color-scheme', theme);
        this.updateThemeIcon(theme);
    }
    
    updateThemeIcon(theme) {
        this.themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    
    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }
}

// Smooth scrolling for navigation links
class SmoothScroll {
    constructor() {
        this.init();
    }
    
    init() {
        // Handle navigation link clicks
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const targetId = anchor.getAttribute('href');
                
                // Skip empty anchors
                if (targetId === '#') {
                    e.preventDefault();
                    return;
                }
                
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    this.scrollToElement(targetElement);
                }
            });
        });
    }
    
    scrollToElement(element) {
        const headerHeight = document.querySelector('.header').offsetHeight;
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerHeight - 20;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
}

// Intersection Observer for animations
class AnimationObserver {
    constructor() {
        this.observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        this.init();
    }
    
    init() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver(
                this.handleIntersection.bind(this),
                this.observerOptions
            );
            
            // Observe feature cards and platform cards
            document.querySelectorAll('.feature-card, .platform-card').forEach(card => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                card.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
                this.observer.observe(card);
            });
        }
    }
    
    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                this.observer.unobserve(entry.target);
            }
        });
    }
}

// Enhanced interactions
class InteractionHandler {
    constructor() {
        this.init();
    }
    
    init() {
        this.handleDownloadClicks();
        this.handleKeyboardNavigation();
    }
    
    handleDownloadClicks() {
        // Add click analytics or tracking here if needed
        document.querySelectorAll('.platform-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (card.classList.contains('platform-card--disabled')) {
                    e.preventDefault();
                    this.showComingSoonMessage(card);
                }
            });
        });
    }
    
    showComingSoonMessage(card) {
        const platform = card.querySelector('.platform-card__name').textContent;
        
        // Create temporary message
        const message = document.createElement('div');
        message.textContent = `${platform} version coming soon!`;
        message.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--color-surface);
            color: var(--color-text);
            padding: 16px 24px;
            border-radius: 8px;
            border: 1px solid var(--color-border);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            font-weight: 500;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        `;
        
        document.body.appendChild(message);
        
        // Remove message after 2 seconds
        setTimeout(() => {
            message.remove();
        }, 2000);
    }
    
    handleKeyboardNavigation() {
        // Enhanced keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close any open modals or messages
                document.querySelectorAll('[style*="position: fixed"]').forEach(el => {
                    if (el.textContent.includes('coming soon')) {
                        el.remove();
                    }
                });
            }
        });
    }
}

// Performance optimizations
class PerformanceOptimizer {
    constructor() {
        this.init();
    }
    
    init() {
        this.optimizeImages();
        this.handleResize();
    }
    
    optimizeImages() {
        // Lazy load images if any are added later
        if ('loading' in HTMLImageElement.prototype) {
            document.querySelectorAll('img').forEach(img => {
                img.loading = 'lazy';
            });
        }
    }
    
    handleResize() {
        let resizeTimeout;
        
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                // Trigger any necessary recalculations
                this.updateViewportHeight();
            }, 250);
        });
        
        // Initial call
        this.updateViewportHeight();
    }
    
    updateViewportHeight() {
        // Fix for mobile browsers with dynamic viewport height
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
    new SmoothScroll();
    new AnimationObserver();
    new InteractionHandler();
    new PerformanceOptimizer();
});

// Handle external link security
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('a[target="_blank"]').forEach(link => {
        link.setAttribute('rel', 'noopener noreferrer');
    });
});