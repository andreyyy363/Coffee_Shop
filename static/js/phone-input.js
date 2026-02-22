/**
 * Phone Input Component with Country Selector
 * KAVASOUL Coffee Shop
 */
(function () {
    'use strict';

    // Country data with flag URLs (using flagcdn.com for high-quality flags)
    // format: pattern with X for digits and space for separators
    const COUNTRIES = [
        { code: 'UA', name: 'Україна', dial: '+380', maxLength: 9, placeholder: '50 123 45 67', format: 'XX XXX XX XX' },
        { code: 'PL', name: 'Polska', dial: '+48', maxLength: 9, placeholder: '500 123 456', format: 'XXX XXX XXX' },
        { code: 'US', name: 'USA', dial: '+1', maxLength: 10, placeholder: '202 555 0123', format: 'XXX XXX XXXX' },
        { code: 'DE', name: 'Deutschland', dial: '+49', maxLength: 11, placeholder: '151 1234 5678', format: 'XXX XXXX XXXX' },
        { code: 'GB', name: 'United Kingdom', dial: '+44', maxLength: 10, placeholder: '7911 123456', format: 'XXXX XXXXXX' },
        { code: 'FR', name: 'France', dial: '+33', maxLength: 9, placeholder: '6 12 34 56 78', format: 'X XX XX XX XX' },
        { code: 'IT', name: 'Italia', dial: '+39', maxLength: 10, placeholder: '312 345 6789', format: 'XXX XXX XXXX' },
        { code: 'CZ', name: 'Česko', dial: '+420', maxLength: 9, placeholder: '601 123 456', format: 'XXX XXX XXX' },
        { code: 'ES', name: 'España', dial: '+34', maxLength: 9, placeholder: '612 345 678', format: 'XXX XXX XXX' },
        { code: 'NL', name: 'Nederland', dial: '+31', maxLength: 9, placeholder: '6 1234 5678', format: 'X XXXX XXXX' },
    ];

    // Get flag URL
    function getFlagUrl(countryCode) {
        return `https://flagcdn.com/w40/${countryCode.toLowerCase()}.png`;
    }

    // Default country (Ukraine)
    const DEFAULT_COUNTRY_CODE = 'UA';

    /**
     * Initialize all phone inputs on the page
     */
    function initPhoneInputs() {
        document.querySelectorAll('[data-phone-input]').forEach(container => {
            if (container.dataset.initialized) return;
            container.dataset.initialized = 'true';
            createPhoneInput(container);
        });
    }

    /**
     * Create a phone input component
     */
    function createPhoneInput(container) {
        const existingInput = container.querySelector('input[type="tel"], input[name*="phone"]');
        const inputName = container.dataset.phoneName || (existingInput ? existingInput.name : 'phone');
        const isRequired = container.dataset.phoneRequired === 'true' || (existingInput && existingInput.required);
        const isCompact = container.dataset.phoneCompact === 'true';
        
        // Parse existing value
        let initialCountry = DEFAULT_COUNTRY_CODE;
        let initialNumber = '';
        
        if (existingInput && existingInput.value) {
            const parsed = parsePhoneNumber(existingInput.value);
            initialCountry = parsed.countryCode;
            initialNumber = parsed.number;
        }

        const country = COUNTRIES.find(c => c.code === initialCountry) || COUNTRIES[0];

        // Build HTML
        const wrapper = document.createElement('div');
        wrapper.className = 'phone-input-wrapper' + (isCompact ? ' compact' : '');
        wrapper.innerHTML = `
            <div class="phone-country-selector" tabindex="0">
                <img class="phone-country-flag" src="${getFlagUrl(country.code)}" alt="${country.code}">
                <span class="phone-country-code">${country.dial}</span>
                <span class="phone-country-arrow">▼</span>
                <div class="phone-country-dropdown">
                    ${COUNTRIES.map(c => `
                        <div class="phone-country-option${c.code === country.code ? ' selected' : ''}" data-country="${c.code}">
                            <img class="phone-country-flag" src="${getFlagUrl(c.code)}" alt="${c.code}">
                            <span class="phone-country-option-name">${c.name}</span>
                            <span class="phone-country-option-code">${c.dial}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <input type="tel" class="phone-number-input" 
                   placeholder="${country.placeholder}" 
                   maxlength="${country.maxLength + 3}"
                   value="${initialNumber}"
                   ${isRequired ? 'required' : ''}>
            <div class="phone-hidden-inputs">
                <input type="hidden" name="${inputName}" value="${country.dial}${initialNumber.replace(/\s/g, '')}">
            </div>
        `;

        // Remove existing input and add new component
        if (existingInput) {
            existingInput.remove();
        }
        container.innerHTML = '';
        container.appendChild(wrapper);

        // Setup event listeners
        setupEventListeners(wrapper, inputName);
    }

    /**
     * Parse a phone number string to extract country code and number
     */
    function parsePhoneNumber(value) {
        value = value.trim();
        
        // Try to match against known country codes
        for (const country of COUNTRIES) {
            if (value.startsWith(country.dial)) {
                return {
                    countryCode: country.code,
                    number: formatDisplayNumber(value.slice(country.dial.length), country)
                };
            }
        }

        // If starts with +, try to find closest match
        if (value.startsWith('+')) {
            for (const country of COUNTRIES) {
                const dialNoPlus = country.dial.slice(1);
                const valueNoPlus = value.slice(1);
                if (valueNoPlus.startsWith(dialNoPlus)) {
                    return {
                        countryCode: country.code,
                        number: formatDisplayNumber(valueNoPlus.slice(dialNoPlus.length), country)
                    };
                }
            }
        }

        // Default to Ukraine with the raw number
        return {
            countryCode: DEFAULT_COUNTRY_CODE,
            number: value.replace(/[^\d]/g, '')
        };
    }

    /**
     * Format number for display (add spaces according to country format)
     */
    function formatDisplayNumber(number, country) {
        // Remove non-digits
        number = number.replace(/[^\d]/g, '');
        if (!number) return '';
        
        const format = country.format || 'XXX XXX XXX'; // fallback format
        let result = '';
        let digitIndex = 0;
        
        for (let i = 0; i < format.length && digitIndex < number.length; i++) {
            if (format[i] === 'X') {
                result += number[digitIndex];
                digitIndex++;
            } else {
                result += format[i];
            }
        }
        
        // Add remaining digits if any (exceeds format)
        while (digitIndex < number.length) {
            result += number[digitIndex];
            digitIndex++;
        }
        
        return result.trim();
    }

    /**
     * Setup event listeners for the phone input
     */
    function setupEventListeners(wrapper, inputName) {
        const selector = wrapper.querySelector('.phone-country-selector');
        const dropdown = wrapper.querySelector('.phone-country-dropdown');
        const numberInput = wrapper.querySelector('.phone-number-input');
        const hiddenInput = wrapper.querySelector(`input[name="${inputName}"]`);
        
        let currentCountry = COUNTRIES.find(c => 
            wrapper.querySelector('.phone-country-code').textContent === c.dial
        ) || COUNTRIES[0];

        function openDropdown() {
            dropdown.classList.add('show');
            selector.setAttribute('aria-expanded', 'true');
        }

        function closeDropdown() {
            dropdown.classList.remove('show');
            selector.setAttribute('aria-expanded', 'false');
        }

        function toggleDropdown() {
            if (dropdown.classList.contains('show')) {
                closeDropdown();
            } else {
                openDropdown();
            }
        }

        selector.setAttribute('aria-expanded', 'false');

        // Toggle dropdown (click/touch)
        selector.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleDropdown();
        });

        selector.addEventListener('touchstart', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleDropdown();
        });

        // Prevent dropdown click from bubbling to document
        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Close dropdown on outside click/touch
        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) {
                closeDropdown();
            }
        });

        document.addEventListener('touchstart', (e) => {
            if (!wrapper.contains(e.target)) {
                closeDropdown();
            }
        });

        // Keyboard navigation for selector
        selector.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleDropdown();
            } else if (e.key === 'Escape') {
                closeDropdown();
            }
        });

        // Country selection
        dropdown.querySelectorAll('.phone-country-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const countryCode = option.dataset.country;
                const country = COUNTRIES.find(c => c.code === countryCode);
                if (!country) return;

                currentCountry = country;

                // Update display
                wrapper.querySelector('.phone-country-flag').src = getFlagUrl(country.code);
                wrapper.querySelector('.phone-country-code').textContent = country.dial;
                numberInput.placeholder = country.placeholder;
                numberInput.maxLength = country.maxLength + 3; // Allow for spaces

                // Update selected state
                dropdown.querySelectorAll('.phone-country-option').forEach(opt => {
                    opt.classList.toggle('selected', opt.dataset.country === countryCode);
                });

                // Update hidden input
                updateHiddenInput();

                // Close dropdown and focus input
                dropdown.classList.remove('show');
                numberInput.focus();
            });
        });

        // Number input - filter and format on-the-fly
        numberInput.addEventListener('input', (e) => {
            let value = e.target.value;
            
            // Keep only digits (remove spaces and non-digits)
            const digitsOnly = value.replace(/[^\d]/g, '');
            
            // Limit digits count
            const limitedDigits = digitsOnly.slice(0, currentCountry.maxLength);
            
            // Format with spaces
            const formatted = formatDisplayNumber(limitedDigits, currentCountry);
            
            // Get cursor position before update
            const cursorPos = e.target.selectionStart;
            const oldLength = value.length;
            
            // Update value
            e.target.value = formatted;
            
            // Adjust cursor position (account for added/removed spaces)
            const newLength = formatted.length;
            const diff = newLength - oldLength;
            const newCursorPos = cursorPos + diff;
            
            // Restore cursor position
            if (newCursorPos >= 0 && newCursorPos <= newLength) {
                e.target.setSelectionRange(newCursorPos, newCursorPos);
            }
            
            updateHiddenInput();
        });

        // Format on blur
        numberInput.addEventListener('blur', () => {
            const digitsOnly = numberInput.value.replace(/[^\d]/g, '');
            numberInput.value = formatDisplayNumber(digitsOnly, currentCountry);
            updateHiddenInput();
        });

        function updateHiddenInput() {
            const digitsOnly = numberInput.value.replace(/[^\d]/g, '');
            hiddenInput.value = currentCountry.dial + digitsOnly;
        }

        // Validation styling
        const form = wrapper.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => {
                const digitsOnly = numberInput.value.replace(/[^\d]/g, '');
                const isRequired = wrapper.hasAttribute('data-phone-required') || numberInput.required;
                if (isRequired && digitsOnly.length < 7) {
                    e.preventDefault();
                    wrapper.classList.add('is-invalid');
                    // Show or update error message
                    let errEl = wrapper.parentElement.querySelector('.phone-error-message');
                    if (!errEl) {
                        errEl = document.createElement('div');
                        errEl.className = 'phone-error-message text-danger small mt-1';
                        wrapper.parentElement.appendChild(errEl);
                    }
                    errEl.textContent = 'Please enter a valid phone number (at least 7 digits)';
                } else if (digitsOnly.length > 0 && digitsOnly.length < 7) {
                    e.preventDefault();
                    wrapper.classList.add('is-invalid');
                    let errEl = wrapper.parentElement.querySelector('.phone-error-message');
                    if (!errEl) {
                        errEl = document.createElement('div');
                        errEl.className = 'phone-error-message text-danger small mt-1';
                        wrapper.parentElement.appendChild(errEl);
                    }
                    errEl.textContent = 'Phone number is too short (at least 7 digits)';
                } else {
                    wrapper.classList.remove('is-invalid');
                    const errEl = wrapper.parentElement.querySelector('.phone-error-message');
                    if (errEl) errEl.remove();
                }
            });

            // Clear error on input
            numberInput.addEventListener('input', () => {
                wrapper.classList.remove('is-invalid');
                const errEl = wrapper.parentElement.querySelector('.phone-error-message');
                if (errEl) errEl.remove();
            });
        }
    }

    /**
     * Public API to reinitialize (for dynamically loaded content)
     */
    window.PhoneInput = {
        init: initPhoneInputs,
        COUNTRIES: COUNTRIES
    };

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', initPhoneInputs);

    // Also initialize on turbo/ajax loads if applicable
    document.addEventListener('turbo:load', initPhoneInputs);
})();
