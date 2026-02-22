/**
 * Client-side form validation for KAVASOUL
 */
(function () {
    'use strict';

    const PHONE_PATTERN = /^\+?[0-9\s\-\(\)]{7,20}$/;
    const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function showError(input, message) {
        clearError(input);
        input.classList.add('is-invalid');
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        input.parentNode.appendChild(feedback);
    }

    function clearError(input) {
        input.classList.remove('is-invalid');
        const existing = input.parentNode.querySelector('.invalid-feedback');
        if (existing) existing.remove();
    }

    function clearAllErrors(form) {
        form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    }

    /* ---------- Phone fields ---------- */
    function validatePhone(input) {
        const val = input.value.trim();
        if (input.required && !val) {
            showError(input, 'Phone number is required');
            return false;
        }
        if (val && !PHONE_PATTERN.test(val)) {
            showError(input, 'Enter a valid phone number (digits, +, spaces, dashes, parentheses)');
            return false;
        }
        clearError(input);
        return true;
    }

    /* ---------- Email fields ---------- */
    function validateEmail(input) {
        const val = input.value.trim();
        if (input.required && !val) {
            showError(input, 'Email is required');
            return false;
        }
        if (val && !EMAIL_PATTERN.test(val)) {
            showError(input, 'Enter a valid email address');
            return false;
        }
        clearError(input);
        return true;
    }

    /* ---------- Password match ---------- */
    function validatePasswordMatch(pw, pwConfirm) {
        if (pw.value && pwConfirm.value && pw.value !== pwConfirm.value) {
            showError(pwConfirm, 'Passwords do not match');
            return false;
        }
        clearError(pwConfirm);
        return true;
    }

    /* ---------- Password strength (min 8 chars) ---------- */
    function validatePasswordStrength(input) {
        const val = input.value;
        if (input.required && !val) {
            showError(input, 'Password is required');
            return false;
        }
        if (val && val.length < 8) {
            showError(input, 'Password must be at least 8 characters');
            return false;
        }
        clearError(input);
        return true;
    }

    /* ---------- Username ---------- */
    function validateUsername(input) {
        // Skip email-as-username login fields
        if (input.type === 'email') {
            clearError(input);
            return true;
        }
        const val = input.value.trim();
        if (val && val.length < 3) {
            showError(input, 'Username must be at least 3 characters');
            return false;
        }
        if (val && !/^[a-zA-Z0-9_]+$/.test(val)) {
            showError(input, 'Username can only contain letters, numbers and underscores');
            return false;
        }
        clearError(input);
        return true;
    }

    /* ---------- Generic required ---------- */
    function validateRequired(input, label) {
        const val = input.value.trim();
        if (input.required && !val) {
            showError(input, (label || 'This field') + ' is required');
            return false;
        }
        clearError(input);
        return true;
    }

    /* ---------- Attach real-time validation on blur/input ---------- */
    function attachLiveValidation() {
        // Phone fields (type=tel or name contains "phone") - skip if inside phone-input component
        document.querySelectorAll('input[type="tel"], input[name="phone"]').forEach(input => {
            // Skip if inside custom phone-input component (handled by phone-input.js)
            if (input.closest('[data-phone-input]')) return;
            
            // Restrict input to allowed phone chars
            input.addEventListener('input', function () {
                this.value = this.value.replace(/[^0-9+\s\-\(\)]/g, '');
            });
            input.addEventListener('blur', function () { validatePhone(this); });
        });

        // Email fields
        document.querySelectorAll('input[type="email"]').forEach(input => {
            input.addEventListener('blur', function () { validateEmail(this); });
        });

        // Username fields
        document.querySelectorAll('input[name="username"]').forEach(input => {
            input.addEventListener('blur', function () { validateUsername(this); });
        });

        // Password confirm - match validation
        document.querySelectorAll('input[name="password_confirm"], input[name="new_password_confirm"]').forEach(confirmInput => {
            const form = confirmInput.closest('form');
            if (!form) return;
            const pwInput = form.querySelector('input[name="password"], input[name="new_password"]');
            if (pwInput) {
                confirmInput.addEventListener('blur', function () { validatePasswordMatch(pwInput, confirmInput); });
            }
        });

        // Password strength
        document.querySelectorAll('input[name="password"], input[name="new_password"]').forEach(input => {
            input.addEventListener('blur', function () { validatePasswordStrength(this); });
        });
    }

    /* ---------- Form submit validation ---------- */
    function attachFormSubmitValidation() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function (e) {
                let isValid = true;

                // Validate all phone fields (skip those in phone-input component)
                form.querySelectorAll('input[type="tel"], input[name="phone"]').forEach(input => {
                    if (input.closest('[data-phone-input]')) return; // Skip custom component
                    if (!validatePhone(input)) isValid = false;
                });

                // Validate all email fields
                form.querySelectorAll('input[type="email"]').forEach(input => {
                    if (!validateEmail(input)) isValid = false;
                });

                // Validate username fields
                form.querySelectorAll('input[name="username"]').forEach(input => {
                    if (!validateUsername(input)) isValid = false;
                });

                // Password strength
                form.querySelectorAll('input[name="password"], input[name="new_password"]').forEach(input => {
                    if (input.value && !validatePasswordStrength(input)) isValid = false;
                });

                // Password match
                const pwConfirm = form.querySelector('input[name="password_confirm"], input[name="new_password_confirm"]');
                if (pwConfirm) {
                    const pwInput = form.querySelector('input[name="password"], input[name="new_password"]');
                    if (pwInput && !validatePasswordMatch(pwInput, pwConfirm)) isValid = false;
                }

                if (!isValid) {
                    e.preventDefault();
                    // Scroll to first error
                    const firstError = form.querySelector('.is-invalid');
                    if (firstError) {
                        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        firstError.focus();
                    }
                }
            });
        });
    }

    /* ---------- Init ---------- */
    document.addEventListener('DOMContentLoaded', function () {
        attachLiveValidation();
        attachFormSubmitValidation();
    });
})();
