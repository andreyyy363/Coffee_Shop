from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse

from .services import ForecastingService
from .inventory_service import InventoryForecastService

import json


def manager_required(view_func):
    """Decorator to require manager or admin role."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, 'Access denied')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


def _parse_forecast_params(request):
    """Parse and clamp forecast parameters from GET request."""
    metric = request.GET.get('metric', 'revenue')
    days_back = int(request.GET.get('days_back', '90'))
    forecast_days = int(request.GET.get('forecast_days', '14'))
    alpha = float(request.GET.get('alpha', '0.3'))
    beta = float(request.GET.get('beta', '0.1'))
    gamma = float(request.GET.get('gamma', '0.2'))

    alpha = max(0.01, min(0.99, alpha))
    beta = max(0.01, min(0.99, beta))
    gamma = max(0.01, min(0.99, gamma))
    days_back = max(14, min(365, days_back))
    forecast_days = max(7, min(60, forecast_days))

    return metric, days_back, forecast_days, alpha, beta, gamma


@manager_required
def sales_forecast(request):
    """Sales forecasting dashboard for managers."""
    metric, days_back, forecast_days, alpha, beta, gamma = _parse_forecast_params(request)

    service = ForecastingService(alpha=alpha, beta=beta, gamma=gamma)
    result = service.generate_forecast(
        metric=metric,
        days_back=days_back,
        forecast_days=forecast_days,
    )

    top_products = list(service.get_product_sales_ranking(days_back))

    context = {
        'result_json': json.dumps(result, default=str),
        'result': result,
        'top_products': top_products,
        'metric': metric,
        'days_back': days_back,
        'forecast_days': forecast_days,
        'alpha': alpha,
        'beta': beta,
        'gamma': gamma,
    }

    return render(request, 'analytics/forecast.html', context)


@manager_required
def forecast_api(request):
    """JSON API for live forecast updates (AJAX)."""
    metric, days_back, forecast_days, alpha, beta, gamma = _parse_forecast_params(request)

    service = ForecastingService(alpha=alpha, beta=beta, gamma=gamma)
    result = service.generate_forecast(
        metric=metric,
        days_back=days_back,
        forecast_days=forecast_days,
    )

    top_products = list(service.get_product_sales_ranking(days_back))
    top_products_data = [
        {'product_name': p['product_name'], 'total_qty': p['total_qty'],
         'total_revenue': float(p['total_revenue'])}
        for p in top_products
    ]

    return JsonResponse({
        'result': json.loads(json.dumps(result, default=str)),
        'top_products': top_products_data,
        'metric': metric,
        'days_back': days_back,
        'forecast_days': forecast_days,
        'alpha': alpha,
        'beta': beta,
        'gamma': gamma,
    })


# ────────────────────────────────────────────────
# Inventory Forecasting Views
# ────────────────────────────────────────────────

def _parse_inventory_params(request):
    """Parse and clamp inventory forecast parameters from GET request."""
    days_back = int(request.GET.get('days_back', '90'))
    forecast_days = int(request.GET.get('forecast_days', '14'))
    lead_time = int(request.GET.get('lead_time', '7'))
    service_level = int(request.GET.get('service_level', '95'))
    alpha = float(request.GET.get('alpha', '0.3'))
    beta = float(request.GET.get('beta', '0.1'))
    gamma = float(request.GET.get('gamma', '0.2'))

    # Clamp values
    alpha = max(0.01, min(0.99, alpha))
    beta = max(0.01, min(0.99, beta))
    gamma = max(0.01, min(0.99, gamma))
    days_back = max(14, min(365, days_back))
    forecast_days = max(7, min(60, forecast_days))
    lead_time = max(1, min(30, lead_time))
    service_level = max(90, min(99, service_level))
    # Snap service level to supported values
    if service_level not in (90, 95, 97, 99):
        service_level = 95

    return days_back, forecast_days, lead_time, service_level, alpha, beta, gamma


@manager_required
def inventory_forecast(request):
    """Inventory forecasting dashboard for managers."""
    days_back, forecast_days, lead_time, service_level, alpha, beta, gamma = _parse_inventory_params(request)

    service = InventoryForecastService(alpha=alpha, beta=beta, gamma=gamma)
    result = service.generate_inventory_forecast(
        days_back=days_back,
        forecast_days=forecast_days,
        lead_time=lead_time,
        service_level=service_level,
    )

    # Prepare chart data for JSON (strip heavy arrays from product list for main page)
    products_chart_data = []
    for p in result['products']:
        products_chart_data.append({
            'product_name': p['product_name'],
            'total_sold': p['total_sold'],
            'avg_daily_demand': p['avg_daily_demand'],
            'forecast_total': p['forecast_total'],
            'safety_stock': p['safety_stock'],
            'reorder_point': p['reorder_point'],
            'recommended_order_qty': p['recommended_order_qty'],
            'trend': p['trend'],
            'demand_pattern': p['demand_pattern'],
            'cv': p['cv'],
        })

    context = {
        'result': result,
        'products_json': json.dumps(products_chart_data, default=str),
        'days_back': days_back,
        'forecast_days': forecast_days,
        'lead_time': lead_time,
        'service_level': service_level,
        'alpha': alpha,
        'beta': beta,
        'gamma': gamma,
    }

    return render(request, 'analytics/inventory_forecast.html', context)


@manager_required
def inventory_forecast_api(request):
    """JSON API for live inventory forecast updates (AJAX)."""
    days_back, forecast_days, lead_time, service_level, alpha, beta, gamma = _parse_inventory_params(request)

    service = InventoryForecastService(alpha=alpha, beta=beta, gamma=gamma)
    result = service.generate_inventory_forecast(
        days_back=days_back,
        forecast_days=forecast_days,
        lead_time=lead_time,
        service_level=service_level,
    )

    # Slim down product data for JSON transfer
    products_data = []
    for p in result['products']:
        products_data.append({
            'product_id': p['product_id'],
            'product_name': p['product_name'],
            'total_sold': p['total_sold'],
            'avg_daily_demand': p['avg_daily_demand'],
            'max_daily_demand': p['max_daily_demand'],
            'demand_std': p['demand_std'],
            'cv': p['cv'],
            'demand_pattern': p['demand_pattern'],
            'days_with_sales': p['days_with_sales'],
            'forecast_total': p['forecast_total'],
            'forecast_avg_daily': p['forecast_avg_daily'],
            'forecast_method': p['forecast_method'],
            'trend': p['trend'],
            'safety_stock': p['safety_stock'],
            'reorder_point': p['reorder_point'],
            'recommended_order_qty': p['recommended_order_qty'],
        })

    return JsonResponse({
        'products': products_data,
        'summary': result['summary'],
        'params': result['params'],
    })


@manager_required
def inventory_product_detail_api(request, product_id):
    """JSON API for single product detailed inventory forecast."""
    days_back, forecast_days, lead_time, service_level, alpha, beta, gamma = _parse_inventory_params(request)

    service = InventoryForecastService(alpha=alpha, beta=beta, gamma=gamma)
    result = service.generate_single_product_forecast(
        product_id=product_id,
        days_back=days_back,
        forecast_days=forecast_days,
        lead_time=lead_time,
        service_level=service_level,
    )

    if result is None:
        return JsonResponse({'error': 'No data for this product'}, status=404)

    return JsonResponse(json.loads(json.dumps(result, default=str)))
