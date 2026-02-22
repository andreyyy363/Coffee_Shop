import json
from decimal import Decimal
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from discounts.models import PromoCode
from products.models import Product, Weight, BeanType
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from .forms import CheckoutForm, UpdateOrderStatusForm, UpdateOrderContactForm



def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        if not created and request.session.session_key:
            session_cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if session_cart and session_cart != cart:
                for item in session_cart.items.all():
                    existing = cart.items.filter(
                        product=item.product,
                        weight=item.weight,
                        bean_type=item.bean_type
                    ).first()
                    if existing:
                        existing.quantity += item.quantity
                        existing.save()
                    else:
                        item.cart = cart
                        item.save()

                session_cart.delete()
    else:
        if not request.session.session_key:
            request.session.create()

        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)

    return cart


def cart_view(request):
    cart = get_or_create_cart(request)
    discount_info = {}
    applied_promo_code = request.session.get('promo_code', '')

    if request.user.is_authenticated and cart.items.exists():
        try:
            from discounts.services import DiscountCalculator
            calculator = DiscountCalculator(request.user)
            discount_info = calculator.calculate_discount(
                cart.subtotal,
                promo_code=applied_promo_code if applied_promo_code else None
            )
        except Exception as e:
            discount_info = {}

    if request.method == 'POST' and request.user.is_authenticated:
        form = CheckoutForm(request.POST)
        if form.is_valid():
            promo_code = request.POST.get('promo_code_applied', applied_promo_code)
            return place_order(request, cart, form, promo_code)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.display_name,
                'address': request.user.address,
                'phone': request.user.phone,
            }
        form = CheckoutForm(initial=initial_data)

    return render(request, 'orders/cart.html', {
        'cart': cart,
        'form': form,
        'discount_info': discount_info,
        'applied_promo_code': applied_promo_code,
    })


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    weight_id = request.POST.get('weight')
    bean_type_id = request.POST.get('bean_type')
    quantity = int(request.POST.get('quantity', 1))

    if not weight_id or not bean_type_id:
        messages.error(request, 'Please select weight and bean type')
        return redirect('products:detail', slug=product.slug)

    weight = get_object_or_404(Weight, pk=weight_id)
    bean_type = get_object_or_404(BeanType, pk=bean_type_id)

    cart = get_or_create_cart(request)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        weight=weight,
        bean_type=bean_type,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    if request.user.is_authenticated:
        try:
            from recommendations.services import record_interaction
            record_interaction(request.user, product, 'cart')
        except Exception:
            pass

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Added to cart',
            'cart_count': cart.total_items
        })

    messages.success(request, 'Added to cart')
    return redirect('orders:cart')


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    quantity = int(request.POST.get('quantity', 1))

    if quantity > 0:
        item.quantity = quantity
        item.save()
    else:
        item.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            'success': True,
            'cart_count': cart.total_items,
            'subtotal': str(cart.subtotal),
            'total': str(cart.total),
            'item_total': str(item.total_price) if quantity > 0 else '0',
            'has_discount': False,
        }

        if request.user.is_authenticated and cart.items.exists():
            try:
                from discounts.services import DiscountCalculator
                promo_code = request.session.get('promo_code', '')
                calculator = DiscountCalculator(request.user)
                discount_info = calculator.calculate_discount(
                    cart.subtotal,
                    promo_code=promo_code if promo_code else None
                )
                if discount_info.get('is_active') and discount_info.get('total_discount_amount', 0) > 0:
                    response_data['has_discount'] = True
                    response_data['discount_percent'] = str(discount_info['total_discount_percent'])
                    response_data['discount_amount'] = str(discount_info['total_discount_amount'])
                    response_data['original_total'] = str(discount_info['original_amount'] + cart.shipping)
                    response_data['final_total'] = str(discount_info['final_amount'] + cart.shipping)
            except Exception:
                pass

        return JsonResponse(response_data)

    return redirect('orders:cart')


@require_POST
def remove_cart_item(request, item_id):
    """Remove item from cart."""
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            'success': True,
            'cart_count': cart.total_items,
            'subtotal': str(cart.subtotal),
            'total': str(cart.total),
            'has_discount': False,
        }

        if request.user.is_authenticated and cart.items.exists():
            try:
                from discounts.services import DiscountCalculator
                promo_code = request.session.get('promo_code', '')
                calculator = DiscountCalculator(request.user)
                discount_info = calculator.calculate_discount(
                    cart.subtotal,
                    promo_code=promo_code if promo_code else None
                )
                if discount_info.get('is_active') and discount_info.get('total_discount_amount', 0) > 0:
                    response_data['has_discount'] = True
                    response_data['discount_percent'] = str(discount_info['total_discount_percent'])
                    response_data['discount_amount'] = str(discount_info['total_discount_amount'])
                    response_data['original_total'] = str(discount_info['original_amount'] + cart.shipping)
                    response_data['final_total'] = str(discount_info['final_amount'] + cart.shipping)
            except Exception:
                pass

        return JsonResponse(response_data)

    messages.success(request, 'Item removed from cart')
    return redirect('orders:cart')


@require_POST
@login_required
def apply_promo_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()
    except (json.JSONDecodeError, ValueError):
        code = request.POST.get('code', '').strip()

    if not code:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a promo code'
        })

    cart = get_or_create_cart(request)
    if not cart.items.exists():
        return JsonResponse({
            'success': False,
            'message': 'Your cart is empty'
        })

    try:
        from discounts.services import DiscountCalculator
        calculator = DiscountCalculator(request.user)
        is_valid, message, promo_obj = calculator.validate_promo_code(code)

        if is_valid and promo_obj:
            # Check minimum order amount
            if cart.subtotal < promo_obj.min_order_amount:
                return JsonResponse({
                    'success': False,
                    'message': f'Minimum order amount for this code is {promo_obj.min_order_amount} USD'
                })

            request.session['promo_code'] = code
            discount_info = calculator.calculate_discount(cart.subtotal, promo_code=code)

            return JsonResponse({
                'success': True,
                'message': f'Promo code applied! You save {discount_info.get("promo_discount_amount", 0)} USD',
                'discount_info': {
                    'total_discount_amount': str(discount_info.get('total_discount_amount', 0)),
                    'final_amount': str(discount_info.get('final_amount', cart.subtotal)),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error validating promo code'
        })


@login_required
def place_order(request, cart, form, promo_code=None):
    if not cart.items.exists():
        messages.error(request, 'Cart is empty')
        return redirect('orders:cart')

    discount_info = {}
    discount_amount = Decimal('0.00')
    discount_percent = Decimal('0.00')
    final_total = cart.total

    try:
        from discounts.services import DiscountCalculator
        from discounts.models import PromoCodeUsage

        calculator = DiscountCalculator(request.user)
        discount_info = calculator.calculate_discount(
            cart.subtotal,
            promo_code=promo_code if promo_code else None
        )

        if discount_info.get('is_active'):
            discount_amount = discount_info.get('total_discount_amount', Decimal('0.00'))
            discount_percent = discount_info.get('total_discount_percent', Decimal('0.00'))
            final_total = discount_info.get('final_amount', cart.subtotal) + cart.shipping
    except Exception as e:
        pass

    order = Order.objects.create(
        user=request.user,
        full_name=form.cleaned_data['full_name'],
        address=form.cleaned_data['address'],
        phone=form.cleaned_data['phone'],
        payment_type=form.cleaned_data['payment_type'],
        subtotal=cart.subtotal,
        shipping=cart.shipping,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        promo_code_used=promo_code if promo_code and discount_info.get('promo_code_valid') else None,
        total=final_total,
    )

    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            weight=f"{cart_item.weight.grams}g",
            bean_type=cart_item.bean_type.name,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.total_price,
        )

        try:
            from recommendations.services import record_interaction
            record_interaction(request.user, cart_item.product, 'purchase')
        except Exception:
            pass

    # Save discount history
    if discount_info:
        try:
            calculator = DiscountCalculator(request.user)
            calculator.save_discount_history(order, discount_info)

            # Record promo code usage if applicable
            if promo_code and discount_info.get('promo_code_valid'):
                try:
                    promo_obj = PromoCode.objects.get(code__iexact=promo_code)
                    PromoCodeUsage.objects.create(
                        promo_code=promo_obj,
                        user=request.user,
                        order=order,
                        discount_amount=discount_info.get('promo_discount_amount', Decimal('0.00'))
                    )
                    promo_obj.times_used += 1
                    promo_obj.save()
                except PromoCode.DoesNotExist:
                    pass
        except Exception:
            pass

    OrderStatusHistory.objects.create(
        order=order,
        status='processing',
        changed_by=request.user
    )

    cart.items.all().delete()
    if 'promo_code' in request.session:
        del request.session['promo_code']

    messages.success(request, f'Order #{order.order_number} placed successfully!')
    return redirect('orders:order_detail', order_number=order.order_number)


@login_required
def orders_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items', 'status_history'
    ).order_by('-created_at')

    return render(request, 'orders/orders_list.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'status_history__changed_by'),
        order_number=order_number
    )

    if order.user != request.user and not request.user.is_manager:
        messages.error(request, 'Access denied')
        return redirect('orders:list')

    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel order by user."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if not order.can_cancel:
        messages.error(request, 'This order cannot be cancelled')
        return redirect('orders:order_detail', order_number=order_number)

    order.status = 'cancelled_user'
    order.save()

    OrderStatusHistory.objects.create(
        order=order,
        status='cancelled_user',
        comment='Cancelled by user',
        changed_by=request.user
    )

    messages.success(request, 'Order cancelled')
    return redirect('orders:order_detail', order_number=order_number)


# Manager views
def manager_required(view_func):
    """Decorator to check if user is manager."""

    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, 'Access denied')
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return wrapper


@manager_required
def manager_orders(request):
    """Display all orders for managers."""
    orders = Order.objects.all().select_related('user').prefetch_related(
        'items'
    ).order_by('-created_at')

    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    # Search by order number, customer name, or email
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(full_name__icontains=search) |
            Q(user__email__icontains=search)
        )

    return render(request, 'orders/manager_orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status,
        'search_query': search,
    })


@manager_required
def manager_order_detail(request, order_number):
    """Order detail for managers with edit capability."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'status_history__changed_by'),
        order_number=order_number
    )

    status_form = UpdateOrderStatusForm(instance=order)
    contact_form = UpdateOrderContactForm(instance=order)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status':
            old_status = order.status
            status_form = UpdateOrderStatusForm(request.POST, instance=order)
            if status_form.is_valid():
                order = status_form.save()
                if old_status != order.status:
                    OrderStatusHistory.objects.create(
                        order=order,
                        status=order.status,
                        comment=order.manager_comment,
                        changed_by=request.user
                    )
                messages.success(request, 'Status updated')
            else:
                for field, errors in status_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Status: {error}')

        elif action == 'update_contact':
            contact_form = UpdateOrderContactForm(request.POST, instance=order)
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, 'Contact info updated')
            else:
                for field, errors in contact_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.replace("_", " ").title()}: {error}')

        elif action == 'delete':
            order.delete()
            messages.success(request, 'Order deleted')
            return redirect('orders:manager_orders')

        return redirect('orders:manager_order_detail', order_number=order_number)

    return render(request, 'orders/manager_order_detail.html', {
        'order': order,
        'status_form': status_form,
        'contact_form': contact_form,
    })
