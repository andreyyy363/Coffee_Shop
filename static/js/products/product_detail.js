window.initProductDetail = function(config) {
    const basePrice = config.basePrice;
    const discountPercent = config.discountPercent;

    function updateQuantity(change) {
        const input = document.getElementById('quantity');
        let value = parseInt(input.value) + change;
        if (value < 1) value = 1;
        input.value = value;
        updatePrice();
    }

    function updatePrice() {
        const weightInput = document.querySelector('input[name="weight"]:checked');
        const beanTypeInput = document.querySelector('input[name="bean_type"]:checked');
        const quantityInput = document.getElementById('quantity');

        let weightMultiplier = weightInput ? parseFloat(weightInput.dataset.multiplier.replace(',', '.')) : 1;
        let beanTypeMultiplier = beanTypeInput ? parseFloat(beanTypeInput.dataset.multiplier.replace(',', '.')) : 1;
        let quantity = parseInt(quantityInput.value) || 1;

        let originalPrice = basePrice * weightMultiplier * beanTypeMultiplier * quantity;

        // Apply discount if exists
        if (discountPercent > 0) {
            let discountedPrice = originalPrice * (1 - discountPercent / 100);
            document.getElementById('dynamic-price').textContent = discountedPrice.toFixed(2) + ' USD';

            const originalPriceEl = document.getElementById('original-price');
            if (originalPriceEl) {
                originalPriceEl.textContent = originalPrice.toFixed(2) + ' USD';
            }
        } else {
            document.getElementById('dynamic-price').textContent = originalPrice.toFixed(2) + ' USD';
        }
    }

    // Export to global scope
    window.updateQuantity = updateQuantity;
    window.updatePrice = updatePrice;

    // Add event listeners
    document.querySelectorAll('.weight-option').forEach(input => {
        input.addEventListener('change', updatePrice);
    });
    document.querySelectorAll('.bean-type-option').forEach(input => {
        input.addEventListener('change', updatePrice);
    });
    const qtyInput = document.getElementById('quantity');
    if (qtyInput) {
        qtyInput.addEventListener('input', updatePrice);
    }

    // Initialize price
    updatePrice();
};
