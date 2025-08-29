// Telegram WebApp Integration with Cross-Platform Support
class TelegramWebApp {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.user = null;
        this.isReady = false;
        this.platform = this.detectPlatform();
        this.authData = null;
        
        if (this.tg) {
            this.init();
        }
    }
    
    detectPlatform() {
        // Detect if running on mobile or desktop Telegram
        const userAgent = navigator.userAgent.toLowerCase();
        const platform = this.tg?.platform || 'unknown';
        
        const detection = {
            isMobile: /android|iphone|ipad|mobile/.test(userAgent) || platform === 'ios' || platform === 'android',
            isDesktop: /windows|mac|linux/.test(userAgent) || platform === 'tdesktop' || platform === 'weba' || platform === 'web',
            isWebApp: !!this.tg,
            platform: platform,
            userAgent: userAgent,
            version: this.tg?.version || 'unknown'
        };
        
        console.log('Platform detection:', detection);
        return detection;
    }
    
    init() {
        try {
            // Initialize Telegram WebApp
            this.tg.ready();
            this.isReady = true;
            
            // Get user data with platform-specific handling
            this.getUserData();
            
            // Configure WebApp appearance
            this.configureAppearance();
            
            // Set up event listeners
            this.setupEventListeners();
            
            console.log('Telegram WebApp initialized successfully');
            console.log('Platform:', this.platform);
            console.log('User data available:', !!this.user);
        } catch (error) {
            console.error('Error initializing Telegram WebApp:', error);
        }
    }
    
    getUserData() {
        try {
            // Primary method: Get user from initDataUnsafe
            this.user = this.tg.initDataUnsafe?.user;
            this.authData = {
                user: this.user,
                auth_date: this.tg.initDataUnsafe?.auth_date,
                hash: this.tg.initDataUnsafe?.hash,
                query_id: this.tg.initDataUnsafe?.query_id,
                platform: this.platform.platform,
                version: this.platform.version
            };
            
            // Desktop fallback: Sometimes desktop Telegram has different data structure
            if (!this.user && this.platform.isDesktop) {
                console.log('Attempting desktop-specific user data extraction...');
                
                // Try alternative data sources for desktop
                if (this.tg.initData) {
                    try {
                        // Parse initData string (URL encoded format)
                        const params = new URLSearchParams(this.tg.initData);
                        const userString = params.get('user');
                        if (userString) {
                            this.user = JSON.parse(decodeURIComponent(userString));
                            this.authData.user = this.user;
                            this.authData.auth_date = params.get('auth_date');
                            this.authData.hash = params.get('hash');
                            this.authData.query_id = params.get('query_id');
                            console.log('Successfully extracted user data from initData string');
                        }
                    } catch (e) {
                        console.log('Failed to parse initData string:', e);
                    }
                }
            }
            
            // Additional validation for cross-platform consistency
            if (this.user) {
                console.log('User authenticated:', {
                    id: this.user.id,
                    username: this.user.username,
                    first_name: this.user.first_name,
                    platform: this.platform.platform
                });
            }
            
        } catch (error) {
            console.error('Error getting user data:', error);
        }
    }
    
    configureAppearance() {
        if (!this.tg) return;
        
        try {
            // Enable closing confirmation
            this.tg.enableClosingConfirmation();
            
            // Set header color based on theme
            const isDark = document.documentElement.classList.contains('dark');
            this.tg.setHeaderColor(isDark ? '#1f2937' : '#ffffff');
            
            // Expand the WebApp
            this.tg.expand();
            
        } catch (error) {
            console.error('Error configuring WebApp appearance:', error);
        }
    }
    
    setupEventListeners() {
        if (!this.tg) return;
        
        // Listen for theme changes
        this.tg.onEvent('themeChanged', () => {
            this.handleThemeChange();
        });
        
        // Listen for main button clicks
        this.tg.onEvent('mainButtonClicked', () => {
            this.handleMainButtonClick();
        });
        
        // Listen for back button clicks
        this.tg.onEvent('backButtonClicked', () => {
            this.handleBackButtonClick();
        });
    }
    
    handleThemeChange() {
        try {
            const colorScheme = this.tg.colorScheme;
            const isDark = colorScheme === 'dark';
            
            // Update document theme
            if (isDark) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            
            // Update header color
            this.tg.setHeaderColor(isDark ? '#1f2937' : '#ffffff');
            
            // Save theme preference
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            
        } catch (error) {
            console.error('Error handling theme change:', error);
        }
    }
    
    handleMainButtonClick() {
        // Handle main button clicks based on current page
        const path = window.location.pathname;
        
        if (path.includes('/purchase') || path.includes('/sale')) {
            // Submit form if on purchase/sale page
            const form = document.querySelector('form');
            if (form) {
                form.submit();
            }
        }
    }
    
    handleBackButtonClick() {
        // Navigate back
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = '/dashboard';
        }
    }
    
    showMainButton(text, color = '#0088cc') {
        if (!this.tg) return;
        
        try {
            this.tg.MainButton.setText(text);
            this.tg.MainButton.color = color;
            this.tg.MainButton.show();
        } catch (error) {
            console.error('Error showing main button:', error);
        }
    }
    
    hideMainButton() {
        if (!this.tg) return;
        
        try {
            this.tg.MainButton.hide();
        } catch (error) {
            console.error('Error hiding main button:', error);
        }
    }
    
    showBackButton() {
        if (!this.tg) return;
        
        try {
            this.tg.BackButton.show();
        } catch (error) {
            console.error('Error showing back button:', error);
        }
    }
    
    hideBackButton() {
        if (!this.tg) return;
        
        try {
            this.tg.BackButton.hide();
        } catch (error) {
            console.error('Error hiding back button:', error);
        }
    }
    
    close() {
        if (!this.tg) return;
        
        try {
            this.tg.close();
        } catch (error) {
            console.error('Error closing WebApp:', error);
        }
    }
    
    sendData(data) {
        if (!this.tg) return;
        
        try {
            this.tg.sendData(JSON.stringify(data));
        } catch (error) {
            console.error('Error sending data:', error);
        }
    }
    
    // Enhanced authentication method with platform support
    async authenticate() {
        if (!this.user) {
            throw new Error('No user data available for authentication');
        }
        
        // Prepare authentication payload with platform info
        const authPayload = {
            user: this.user,
            auth_date: this.authData.auth_date,
            hash: this.authData.hash,
            query_id: this.authData.query_id,
            platform_info: {
                platform: this.platform.platform,
                version: this.platform.version,
                is_mobile: this.platform.isMobile,
                is_desktop: this.platform.isDesktop,
                user_agent: this.platform.userAgent
            }
        };
        
        console.log('Sending authentication request with platform info:', authPayload.platform_info);
        
        const response = await fetch('/auth/telegram', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(authPayload)
        });
        
        if (!response.ok) {
            throw new Error(`Authentication failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    // Check if authentication is available
    isAuthenticationAvailable() {
        return !!(this.tg && this.user);
    }
    
    // Get debug info for troubleshooting
    getDebugInfo() {
        return {
            hasWebApp: !!this.tg,
            hasUser: !!this.user,
            platform: this.platform,
            authData: this.authData ? {
                hasUser: !!this.authData.user,
                hasAuthDate: !!this.authData.auth_date,
                hasHash: !!this.authData.hash,
                hasQueryId: !!this.authData.query_id
            } : null,
            webAppInfo: this.tg ? {
                platform: this.tg.platform,
                version: this.tg.version,
                colorScheme: this.tg.colorScheme,
                isExpanded: this.tg.isExpanded
            } : null
        };
    }
}

// Initialize Telegram WebApp
window.telegramWebApp = new TelegramWebApp();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TelegramWebApp;
}
