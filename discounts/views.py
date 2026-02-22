from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
import json

from .models import DiscountSettings, CustomerDiscount, PromoCode
from .services import DiscountCalculator, get_discount_curve_data


@login_required
def my_discount_view(request):
    """Show user their personal discount information."""
    calculator = DiscountCalculator(request.user)
    profile = calculator.recalculate_customer_metrics()
    settings = DiscountSettings.get_settings()
    
    # Calculate potential discount for a sample order
    sample_order = Decimal('50.00')
    discount_info = calculator.calculate_discount(sample_order)
    
    # Get discount curve data for visualization
    curve_data = get_discount_curve_data(settings)
    
    context = {
        'profile': profile,
        'settings': settings,
        'discount_info': discount_info,
        'sample_order': sample_order,
        'curve_data': json.dumps(curve_data),
        'first_purchase_bonus': calculator.check_first_purchase_bonus(),
        'birthday_bonus': calculator.check_birthday_bonus(),
    }
    
    return render(request, 'discounts/my_discount.html', context)


@login_required
def validate_promo_code_ajax(request):
    """AJAX endpoint to validate promo code."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    code = request.POST.get('code', '').strip()
    order_total = Decimal(request.POST.get('order_total', '0'))
    
    if not code:
        return JsonResponse({'valid': False, 'message': 'Please enter a promo code'})
    
    calculator = DiscountCalculator(request.user)
    is_valid, message, promo = calculator.validate_promo_code(code)
    
    if not is_valid:
        return JsonResponse({'valid': False, 'message': message})
    
    # Calculate discount
    if promo.min_order_amount > order_total:
        return JsonResponse({
            'valid': False,
            'message': f'Minimum order amount: ${promo.min_order_amount}'
        })
    
    if promo.discount_type == 'percent':
        discount_amount = (order_total * promo.discount_value / 100).quantize(Decimal('0.01'))
        discount_text = f'{promo.discount_value}%'
    else:
        discount_amount = promo.discount_value
        discount_text = f'${promo.discount_value}'
    
    return JsonResponse({
        'valid': True,
        'message': f'Promo code applied: {discount_text} off',
        'discount_amount': str(discount_amount),
        'discount_type': promo.discount_type,
        'discount_value': str(promo.discount_value),
    })


@login_required
def calculate_discount_ajax(request):
    """AJAX endpoint to calculate full discount for cart."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    order_total = Decimal(request.POST.get('order_total', '0'))
    promo_code = request.POST.get('promo_code', '').strip() or None
    
    calculator = DiscountCalculator(request.user)
    discount_info = calculator.calculate_discount(order_total, promo_code)
    
    # Convert Decimals to strings for JSON
    response_data = {
        'is_active': discount_info['is_active'],
        'total_discount_percent': str(discount_info['total_discount_percent']),
        'total_discount_amount': str(discount_info['total_discount_amount']),
        'final_amount': str(discount_info['final_amount']),
        'original_amount': str(discount_info['original_amount']),
        'rfm_score': discount_info.get('rfm_score', 0),
        'promo_code_valid': discount_info.get('promo_code_valid', False),
        'breakdown': []
    }
    
    for item in discount_info['breakdown']:
        breakdown_item = {
            'type': item['type'],
            'name': item['name'],
        }
        if 'percent' in item:
            breakdown_item['percent'] = str(item['percent'])
        if 'amount' in item:
            breakdown_item['amount'] = str(item['amount'])
        response_data['breakdown'].append(breakdown_item)
    
    return JsonResponse(response_data)


# Manager views
def manager_required(view_func):
    """Decorator to require manager or admin role."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role not in ['manager', 'admin'] and not request.user.is_superuser:
            messages.error(request, 'Access denied')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@manager_required
def manager_discount_settings(request):
    """Manage discount system settings."""
    settings = DiscountSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings
        try:
            settings.weight_recency = Decimal(request.POST.get('weight_recency', '0.25'))
            settings.weight_frequency = Decimal(request.POST.get('weight_frequency', '0.35'))
            settings.weight_monetary = Decimal(request.POST.get('weight_monetary', '0.40'))
            
            settings.base_discount_rate = Decimal(request.POST.get('base_discount_rate', '0'))
            settings.max_discount_rate = Decimal(request.POST.get('max_discount_rate', '15'))
            settings.curve_exponent = Decimal(request.POST.get('curve_exponent', '0.7'))
            
            settings.recency_max_days = int(request.POST.get('recency_max_days', '90'))
            settings.frequency_target = int(request.POST.get('frequency_target', '10'))
            settings.monetary_target = Decimal(request.POST.get('monetary_target', '500'))
            
            settings.first_purchase_discount = Decimal(request.POST.get('first_purchase_discount', '5'))
            settings.birthday_discount = Decimal(request.POST.get('birthday_discount', '10'))
            settings.birthday_discount_days = int(request.POST.get('birthday_discount_days', '7'))
            
            settings.is_active = request.POST.get('is_active') == 'on'
            settings.max_total_discount = Decimal(request.POST.get('max_total_discount', '25'))
            
            settings.full_clean()
            settings.save()
            messages.success(request, 'Discount settings updated successfully')
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errs in e.message_dict.items():
                    for err in errs:
                        messages.error(request, f'{field.replace("_", " ").title()}: {err}')
            else:
                messages.error(request, str(e))
        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid value entered: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
        
        return redirect('discounts:manager_settings')
    
    curve_data = get_discount_curve_data(settings)
    
    return render(request, 'discounts/manager_settings.html', {
        'settings': settings,
        'curve_data': json.dumps(curve_data),
    })


@manager_required
def manager_promo_codes(request):
    """Manage promo codes."""
    promo_codes = PromoCode.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            from django.utils import timezone
            from datetime import timedelta
            
            code = request.POST.get('code', '').strip().upper()
            discount_value_str = request.POST.get('discount_value', '').strip()
            
            # Validate required fields
            errors = []
            if not code:
                errors.append('Promo code is required')
            elif PromoCode.objects.filter(code=code).exists():
                errors.append(f'Promo code "{code}" already exists')
            
            if not discount_value_str:
                errors.append('Discount value is required')
            else:
                try:
                    discount_val = Decimal(discount_value_str)
                    if discount_val <= 0:
                        errors.append('Discount value must be greater than 0')
                except Exception:
                    errors.append('Invalid discount value')
            
            if errors:
                for err in errors:
                    messages.error(request, err)
            else:
                try:
                    promo = PromoCode.objects.create(
                        code=code,
                        description=request.POST.get('description', ''),
                        discount_type=request.POST.get('discount_type', 'percent'),
                        discount_value=Decimal(discount_value_str),
                        min_order_amount=Decimal(request.POST.get('min_order_amount', '0')),
                        max_uses=int(request.POST.get('max_uses') or 0) or None,
                        max_uses_per_user=int(request.POST.get('max_uses_per_user', '1')),
                        valid_from=timezone.now(),
                        valid_until=timezone.now() + timedelta(days=int(request.POST.get('valid_days', '30'))),
                        is_active=True,
                    )
                    messages.success(request, f'Promo code "{promo.code}" created')
                except Exception as e:
                    messages.error(request, f'Error creating promo code: {str(e)}')
        
        elif action == 'toggle':
            promo_id = request.POST.get('promo_id')
            promo = get_object_or_404(PromoCode, pk=promo_id)
            promo.is_active = not promo.is_active
            promo.save()
            messages.success(request, f'Promo code "{promo.code}" {"activated" if promo.is_active else "deactivated"}')
        
        elif action == 'delete':
            promo_id = request.POST.get('promo_id')
            promo = get_object_or_404(PromoCode, pk=promo_id)
            code = promo.code
            promo.delete()
            messages.success(request, f'Promo code "{code}" deleted')
        
        return redirect('discounts:manager_promo_codes')
    
    return render(request, 'discounts/manager_promo_codes.html', {
        'promo_codes': promo_codes,
    })


@manager_required
def manager_customer_discounts(request):
    """View customer discount profiles."""
    customers = CustomerDiscount.objects.select_related('user').order_by('-rfm_score')
    
    return render(request, 'discounts/manager_customers.html', {
        'customers': customers,
    })


@manager_required
def manager_recommendation_settings(request):
    """Manage recommendation system settings."""
    from recommendations.models import RecommendationSettings
    
    settings = RecommendationSettings.get_settings()
    
    if request.method == 'POST':
        try:
            # Hybrid weights
            settings.weight_content_based = Decimal(request.POST.get('weight_content_based', '0.35'))
            settings.weight_collaborative = Decimal(request.POST.get('weight_collaborative', '0.40'))
            settings.weight_popularity = Decimal(request.POST.get('weight_popularity', '0.25'))
            
            # Feature weights
            settings.feature_country_weight = Decimal(request.POST.get('feature_country_weight', '0.25'))
            settings.feature_roast_weight = Decimal(request.POST.get('feature_roast_weight', '0.30'))
            settings.feature_bean_weight = Decimal(request.POST.get('feature_bean_weight', '0.25'))
            settings.feature_price_weight = Decimal(request.POST.get('feature_price_weight', '0.20'))
            
            # Other settings
            settings.time_decay_rate = Decimal(request.POST.get('time_decay_rate', '0.050'))
            settings.min_interactions_for_cf = int(request.POST.get('min_interactions_for_cf', '3'))
            settings.is_active = request.POST.get('is_active') == 'on'
            
            settings.full_clean()
            settings.save()
            messages.success(request, 'Recommendation settings updated successfully')
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errs in e.message_dict.items():
                    for err in errs:
                        messages.error(request, f'{field.replace("_", " ").title()}: {err}')
            else:
                messages.error(request, str(e))
        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid value entered: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
        
        return redirect('discounts:manager_recommendations')
    
    return render(request, 'discounts/manager_recommendations.html', {
        'settings': settings,
    })
