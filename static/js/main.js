// Main application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeFormValidation();
    initializeNotifications();
    initializeTelegramIntegration();
    
    console.log('Founders Management app initialized');
});

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                return false;
            }
        });
        
        // Real-time validation for number inputs
        const numberInputs = form.querySelectorAll('input[type="number"]');
        numberInputs.forEach(input => {
            input.addEventListener('input', function() {
                validateNumberInput(this);
            });
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Specific validation for purchase/sale forms
    if (form.action.includes('/purchase') || form.action.includes('/sale')) {
        isValid = validateTransactionForm(form) && isValid;
    }
    
    return isValid;
}

function validateTransactionForm(form) {
    let isValid = true;
    
    const goldAmount = form.querySelector('input[name="gold_amount"]');
    const unitPrice = form.querySelector('input[name="unit_price"]');
    
    if (goldAmount && parseFloat(goldAmount.value) <= 0) {
        showFieldError(goldAmount, 'Gold amount must be greater than 0');
        isValid = false;
    }
    
    if (unitPrice && parseFloat(unitPrice.value) <= 0) {
        showFieldError(unitPrice, 'Unit price must be greater than 0');
        isValid = false;
    }
    
    // Additional validation for sales
    if (form.action.includes('/sale')) {
        const maxAmount = parseFloat(goldAmount?.getAttribute('max') || 0);
        const currentAmount = parseFloat(goldAmount?.value || 0);
        
        if (currentAmount > maxAmount) {
            showFieldError(goldAmount, `Cannot sell more than ${maxAmount}g (available inventory)`);
            isValid = false;
        }
    }
    
    return isValid;
}

function validateNumberInput(input) {
    const value = parseFloat(input.value);
    const min = parseFloat(input.getAttribute('min') || 0);
    const max = parseFloat(input.getAttribute('max') || Infinity);
    
    if (value < min) {
        showFieldError(input, `Value must be at least ${min}`);
    } else if (value > max) {
        showFieldError(input, `Value cannot exceed ${max}`);
    } else {
        clearFieldError(input);
    }
}

function showFieldError(field, message) {
    // Remove existing error
    clearFieldError(field);
    
    // Add error styling
    field.classList.add('border-red-500', 'border-red-300');
    field.classList.remove('border-gray-300', 'dark:border-gray-600');
    
    // Create error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error text-red-600 dark:text-red-400 text-xs mt-1';
    errorDiv.textContent = message;
    
    // Insert after the field
    field.parentNode.insertBefore(errorDiv, field.nextSibling);
}

function clearFieldError(field) {
    // Remove error styling
    field.classList.remove('border-red-500', 'border-red-300');
    field.classList.add('border-gray-300', 'dark:border-gray-600');
    
    // Remove error message
    const errorDiv = field.parentNode.querySelector('.field-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Notification system
function initializeNotifications() {
    // Auto-hide flash messages after 5 seconds (but not admin database sections)
    const flashMessages = document.querySelectorAll('.flash-message, [class*="bg-red-50"]:not(.admin-section), [class*="bg-green-50"]:not(.admin-section)');
    flashMessages.forEach(message => {
        // Skip admin database reset sections
        if (message.querySelector('form[action*="reset"]') || message.closest('.admin-database-section')) {
            return;
        }
        
        setTimeout(() => {
            if (message.parentNode) {
                message.style.transition = 'opacity 0.5s ease-in-out';
                message.style.opacity = '0';
                setTimeout(() => {
                    if (message.parentNode) {
                        message.remove();
                    }
                }, 500);
            }
        }, 5000);
    });
}

// Telegram WebApp integration
function initializeTelegramIntegration() {
    const currentPath = window.location.pathname;
    const tg = window.telegramWebApp;
    
    if (!tg || !tg.isReady) return;
    
    // Configure navigation based on current page
    switch (currentPath) {
        case '/purchase':
        case '/sale':
            tg.showBackButton();
            tg.showMainButton('Save', '#0088cc');
            break;
            
        case '/admin':
        case '/history':
            tg.showBackButton();
            break;
            
        case '/dashboard':
        case '/':
            tg.hideBackButton();
            tg.hideMainButton();
            break;
            
        default:
            tg.showBackButton();
            break;
    }
}

// Utility functions
function formatCurrency(amount, currency = 'CAD') {
    if (currency === 'IRR') {
        return `${amount.toLocaleString()} ﷼`;
    } else {
        return `$${amount.toFixed(2)} ${currency}`;
    }
}

function formatWeight(grams) {
    return `${grams.toFixed(2)}g`;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    
    // Show user-friendly error message
    if (e.error && e.error.message) {
        showNotification('An error occurred. Please try again.', 'error');
    }
});

// Show notification function
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg border ${
        type === 'error' 
            ? 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/50 dark:border-red-700 dark:text-red-200'
            : type === 'success'
            ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/50 dark:border-green-700 dark:text-green-200'
            : 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/50 dark:border-blue-700 dark:text-blue-200'
    }`;
    
    notification.innerHTML = `
        <div class="flex items-center">
            <i data-feather="${type === 'error' ? 'alert-circle' : type === 'success' ? 'check-circle' : 'info'}" class="w-5 h-5 mr-2"></i>
            ${message}
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Re-render feather icons
    if (window.feather) {
        feather.replace();
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.transition = 'opacity 0.5s ease-in-out';
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 500);
        }
    }, 5000);
}

// Export utility functions for global use
window.FoundersManagement = {
    formatCurrency,
    formatWeight,
    showNotification,
    debounce
};
