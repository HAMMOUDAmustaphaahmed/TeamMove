/**
 * GESTION PERSONNELS - SCRIPTS GLOBAUX
 * Sécurité et fonctionnalités interactives
 */

// ==========================================
// CONFIGURATION GLOBALE
// ==========================================

const CONFIG = {
    apiBaseUrl: '/api',
    debounceDelay: 300,
    animationDuration: 300,
    itemsPerPage: 10
};

// ==========================================
// UTILITAIRES DE SÉCURITÉ
// ==========================================

const SecurityUtils = {
    /**
     * Échappe les caractères HTML pour prévenir XSS
     */
    escapeHtml: (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Valide une entrée utilisateur
     */
    sanitizeInput: (input, type = 'text') => {
        if (typeof input !== 'string') return '';
        
        // Supprime les balises script et les événements on*
        let clean = input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        clean = clean.replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '');
        
        switch(type) {
            case 'email':
                return clean.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/) ? clean : '';
            case 'number':
                return !isNaN(clean) ? clean : '';
            case 'alphanumeric':
                return clean.replace(/[^a-zA-Z0-9]/g, '');
            default:
                return clean.trim();
        }
    },

    /**
     * Génère un token CSRF si nécessaire
     */
    getCsrfToken: () => {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
};

// ==========================================
// GESTION DES NOTIFICATIONS
// ==========================================

const Notifications = {
    /**
     * Affiche une notification toast
     */
    show: (message, type = 'info', duration = 3000) => {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 5px 15px rgba(0,0,0,0.2);';
        toast.innerHTML = `
            ${SecurityUtils.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, duration);
    },

    success: (msg) => Notifications.show(msg, 'success'),
    error: (msg) => Notifications.show(msg, 'danger'),
    warning: (msg) => Notifications.show(msg, 'warning'),
    info: (msg) => Notifications.show(msg, 'info')
};

// ==========================================
// VALIDATION DE FORMULAIRES
// ==========================================

const FormValidator = {
    /**
     * Valide un formulaire complet
     */
    validate: (form) => {
        const inputs = form.querySelectorAll('input, select, textarea');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!FormValidator.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    },

    /**
     * Valide un champ individuel
     */
    validateField: (input) => {
        const value = input.value.trim();
        const type = input.type;
        let isValid = true;
        let errorMsg = '';

        // Validation requise
        if (input.required && !value) {
            isValid = false;
            errorMsg = 'Ce champ est requis';
        }

        // Validation par type
        if (value) {
            switch(type) {
                case 'email':
                    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    if (!emailRegex.test(value)) {
                        isValid = false;
                        errorMsg = 'Email invalide';
                    }
                    break;
                    
                case 'password':
                    if (value.length < 8) {
                        isValid = false;
                        errorMsg = 'Minimum 8 caractères';
                    } else if (!/(?=.*\d)(?=.*[a-z])(?=.*[A-Z])/.test(value)) {
                        isValid = false;
                        errorMsg = 'Doit contenir majuscule, minuscule et chiffre';
                    }
                    break;
                    
                case 'number':
                    if (isNaN(value) || value < 0) {
                        isValid = false;
                        errorMsg = 'Nombre invalide';
                    }
                    break;
            }

            // Validation pattern personnalisé
            if (input.pattern && value) {
                const regex = new RegExp(input.pattern);
                if (!regex.test(value)) {
                    isValid = false;
                    errorMsg = input.title || 'Format invalide';
                }
            }
        }

        // Mise à jour UI
        FormValidator.updateFieldUI(input, isValid, errorMsg);
        return isValid;
    },

    /**
     * Met à jour l'apparence du champ
     */
    updateFieldUI: (input, isValid, errorMsg) => {
        // Supprime les anciens messages
        const existingFeedback = input.parentElement.querySelector('.invalid-feedback');
        if (existingFeedback) existingFeedback.remove();

        input.classList.remove('is-valid', 'is-invalid');
        
        if (input.value.trim() === '') return;

        if (isValid) {
            input.classList.add('is-valid');
        } else {
            input.classList.add('is-invalid');
            if (errorMsg) {
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = errorMsg;
                input.parentElement.appendChild(feedback);
            }
        }
    },

    /**
     * Initialise la validation en temps réel
     */
    initRealTimeValidation: (formSelector) => {
        const forms = document.querySelectorAll(formSelector);
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            
            inputs.forEach(input => {
                // Validation au blur
                input.addEventListener('blur', () => {
                    FormValidator.validateField(input);
                });

                // Validation au input (avec debounce)
                let timeout;
                input.addEventListener('input', () => {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        FormValidator.validateField(input);
                    }, CONFIG.debounceDelay);
                });
            });

            // Validation à la soumission
            form.addEventListener('submit', (e) => {
                if (!FormValidator.validate(form)) {
                    e.preventDefault();
                    Notifications.error('Veuillez corriger les erreurs du formulaire');
                }
            });
        });
    }
};

// ==========================================
// CONFIRMATIONS ET DIALOGUES
// ==========================================

const Dialogs = {
    /**
     * Demande une confirmation avant action destructive
     */
    confirmDelete: (message = 'Êtes-vous sûr de vouloir supprimer cet élément ?') => {
        return new Promise((resolve) => {
            if (confirm(message)) {
                resolve(true);
            } else {
                resolve(false);
            }
        });
    },

    /**
     * Crée un modal de confirmation personnalisé
     */
    customConfirm: (options = {}) => {
        const {
            title = 'Confirmation',
            message = 'Êtes-vous sûr ?',
            confirmText = 'Confirmer',
            cancelText = 'Annuler',
            type = 'danger'
        } = options;

        return new Promise((resolve) => {
            const modalId = 'customConfirmModal';
            
            // Supprime l'ancien modal s'il existe
            const existingModal = document.getElementById(modalId);
            if (existingModal) existingModal.remove();

            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header bg-${type} text-white">
                                <h5 class="modal-title"><i class="fas fa-exclamation-triangle me-2"></i>${title}</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p class="mb-0">${SecurityUtils.escapeHtml(message)}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                                <button type="button" class="btn btn-${type}" id="confirmBtn">${confirmText}</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();

            document.getElementById('confirmBtn').addEventListener('click', () => {
                resolve(true);
                modal.hide();
            });

            document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
                resolve(false);
                document.getElementById(modalId).remove();
            });
        });
    }
};

// ==========================================
// REQUÊTES API SÉCURISÉES
// ==========================================

const ApiClient = {
    /**
     * Effectue une requête fetch avec gestion d'erreurs
     */
    request: async (url, options = {}) => {
        const defaultOptions = {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
                'X-CSRFToken': SecurityUtils.getCsrfToken()
            },
            credentials: 'same-origin'
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            Notifications.error('Erreur de communication avec le serveur');
            throw error;
        }
    },

    get: (url) => ApiClient.request(url),
    
    post: (url, data) => ApiClient.request(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
};

// ==========================================
// FONCTIONNALITÉS SPÉCIFIQUES
// ==========================================

const AppFeatures = {
    /**
     * Initialise la recherche dynamique dans les tableaux
     */
    initTableSearch: (tableId, searchInputId) => {
        const searchInput = document.getElementById(searchInputId);
        const table = document.getElementById(tableId);
        
        if (!searchInput || !table) return;

        let timeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const term = SecurityUtils.sanitizeInput(e.target.value).toLowerCase();
                const rows = table.querySelectorAll('tbody tr');
                
                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(term) ? '' : 'none';
                });
            }, CONFIG.debounceDelay);
        });
    },

    /**
     * Exporte un tableau vers CSV
     */
    exportTableToCSV: (tableId, filename = 'export.csv') => {
        const table = document.getElementById(tableId);
        if (!table) return;

        let csv = [];
        const rows = table.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const rowData = Array.from(cols).map(col => {
                let data = col.textContent.replace(/"/g, '""');
                return `"${data}"`;
            });
            csv.push(rowData.join(';'));
        });

        const csvContent = '\uFEFF' + csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    },

    /**
     * Gère l'affichage du mot de passe
     */
    initPasswordToggle: () => {
        document.querySelectorAll('.password-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                const input = document.querySelector(e.target.dataset.target);
                const icon = e.target.querySelector('i');
                
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    input.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            });
        });
    },

    /**
     * Calcul la force du mot de passe
     */
    checkPasswordStrength: (password) => {
        let strength = 0;
        if (password.length >= 8) strength += 25;
        if (password.match(/[a-z]+/)) strength += 25;
        if (password.match(/[A-Z]+/)) strength += 25;
        if (password.match(/[0-9]+/)) strength += 25;
        return strength;
    }
};

// ==========================================
// INITIALISATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialisation de la validation des formulaires
    FormValidator.initRealTimeValidation('form');
    
    // Initialisation des tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
    
    // Protection contre le double envoi de formulaire
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Chargement...';
            }
        });
    });

    // Animation d'entrée des éléments
    document.querySelectorAll('.animate-fade-in').forEach((el, index) => {
        el.style.animationDelay = `${index * 0.1}s`;
    });

    console.log('🚀 Gestion Personnels - Application chargée avec succès');
    console.log('🔒 Sécurité: XSS Protection, CSRF Tokens, Input Validation actifs');
});

// Export pour utilisation globale
window.App = {
    SecurityUtils,
    Notifications,
    FormValidator,
    Dialogs,
    ApiClient,
    AppFeatures,
    CONFIG
};