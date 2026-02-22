def cart_count(request):
    """Context processor to add cart count to all templates."""
    count = 0
    if request.user.is_authenticated:
        cart = getattr(request.user, 'cart', None)
        if cart:
            count = cart.total_items
    else:
        from .models import Cart
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
            if cart:
                count = cart.total_items
    return {'cart_count': count}
