// Telegram WebApp Integration
class TelegramWebApp {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.user = null;
        this.isReady = false;
        
        if (this.tg) {
            this.init();
        }
    }
    
    init() {
        try {
            // Initialize Telegram WebApp
            this.tg.ready();
            this.isReady = true;
            
            // Get user data
            this.user = this.tg.initDataUnsafe?.user;
            
            // Configure WebApp appearance
            this.configureAppearance();
            
            // Set up event listeners
            this.setupEventListeners();
            
            console.log('Telegram WebApp initialized successfully');
        } catch (error) {
            console.error('Error initializing Telegram WebApp:', error);
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
}

// Initialize Telegram WebApp
window.telegramWebApp = new TelegramWebApp();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TelegramWebApp;
}
