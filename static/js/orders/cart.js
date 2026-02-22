const CartConfig = {
    applyPromoUrl: ''
};

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initCart(config) {
    if (config.applyPromoUrl) CartConfig.applyPromoUrl = config.applyPromoUrl;

    const promoInput = document.getElementById('promo-code-input');
    if (promoInput) {
        promoInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                applyPromoCode();
            }
        });
    }
}

function updateCartItem(itemId, change) {
    const item = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
    if (!item) return;

    const quantitySpan = item.querySelector('.item-quantity');
    let newQuantity = parseInt(quantitySpan.textContent) + change;

    if (newQuantity < 1) {
        removeCartItem(itemId);
        return;
    }

    const csrftoken = getCookie('csrftoken');

    fetch(`/orders/cart/update/${itemId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `quantity=${newQuantity}`
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                quantitySpan.textContent = newQuantity;
                item.querySelector('.item-total').textContent = data.item_total;
                const subtotalEl = document.getElementById('subtotal');
                if (subtotalEl) subtotalEl.textContent = data.subtotal + ' USD';

                // Update with discount info if available
                if (data.has_discount) {
                    const originalTotalEl = document.getElementById('original-total');
                    if (originalTotalEl) {
                        originalTotalEl.textContent = data.original_total + ' USD';
                    }
                    const totalEl = document.getElementById('total');
                    if (totalEl) totalEl.innerHTML = '<strong class="text-primary fs-5">' + data.final_total + ' USD</strong>';

                    const discountAmountEl = document.getElementById('discount-amount');
                    if (discountAmountEl) {
                        discountAmountEl.innerHTML = '<strong>-' + data.discount_amount + ' USD</strong>';
                    }
                } else {
                    const totalEl = document.getElementById('total');
                    if (totalEl) totalEl.innerHTML = '<strong class="text-primary fs-5">' + data.total + ' USD</strong>';
                }

                updateCartBadge(data.cart_count);
            }
        });
}

function removeCartItem(itemId) {
    if (!confirm('Remove this item from cart?')) return;

    const csrftoken = getCookie('csrftoken');

    fetch(`/orders/cart/remove/${itemId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const item = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
                if (item) item.remove();

                const subtotalEl = document.getElementById('subtotal');
                if (subtotalEl) subtotalEl.textContent = data.subtotal + ' USD';

                // Update with discount info if available
                if (data.has_discount) {
                    const originalTotalEl = document.getElementById('original-total');
                    if (originalTotalEl) {
                        originalTotalEl.textContent = data.original_total + ' USD';
                    }
                    const totalEl = document.getElementById('total');
                    if (totalEl) totalEl.innerHTML = '<strong class="text-primary fs-5">' + data.final_total + ' USD</strong>';

                    const discountAmountEl = document.getElementById('discount-amount');
                    if (discountAmountEl) {
                        discountAmountEl.innerHTML = '<strong>-' + data.discount_amount + ' USD</strong>';
                    }
                } else {
                    const totalEl = document.getElementById('total');
                    if (totalEl) totalEl.innerHTML = '<strong class="text-primary fs-5">' + data.total + ' USD</strong>';
                }

                updateCartBadge(data.cart_count);

                if (data.cart_count === 0) {
                    location.reload();
                }
            }
        });
}

function updateCartBadge(count) {
    const badge = document.querySelector('.cart-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
        } else {
            badge.remove();
        }
    }
}

function applyPromoCode() {
    const promoInput = document.getElementById('promo-code-input');
    const code = promoInput.value.trim();
    const messageDiv = document.getElementById('promo-code-message');

    if (!code) {
        messageDiv.style.display = 'block';
        messageDiv.className = 'alert alert-warning mb-3';
        messageDiv.innerHTML = '<i class="bi bi-exclamation-circle me-2"></i>Please enter a promo code';
        return;
    }

    const csrftoken = getCookie('csrftoken');

    fetch(CartConfig.applyPromoUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({code: code})
    })
        .then(response => response.json())
        .then(data => {
            messageDiv.style.display = 'block';

            if (data.success) {
                messageDiv.className = 'alert alert-success mb-3';
                messageDiv.innerHTML = '<i class="bi bi-check-circle me-2"></i>' + data.message;
                const appliedEl = document.getElementById('promo-code-applied');
                if (appliedEl) appliedEl.value = code;

                // Reload page to show updated discount
                location.reload();
            } else {
                messageDiv.className = 'alert alert-danger mb-3';
                messageDiv.innerHTML = '<i class="bi bi-x-circle me-2"></i>' + data.message;
                const appliedEl = document.getElementById('promo-code-applied');
                if (appliedEl) appliedEl.value = '';
            }
        })
        .catch(error => {
            messageDiv.style.display = 'block';
            messageDiv.className = 'alert alert-danger mb-3';
            messageDiv.innerHTML = '<i class="bi bi-x-circle me-2"></i>Error applying promo code';
        });
}

// Global exports
window.updateCartItem = updateCartItem;
window.removeCartItem = removeCartItem;
window.applyPromoCode = applyPromoCode;
window.initCart = initCart;
window.updateCartBadge = updateCartBadge;
