"""
Inventory Forecasting Service.

Predicts required stock levels for each product using demand forecasting
combined with safety stock analysis, reorder point, and recommended
order quantity calculations.
"""

import math
from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product

from .services import ForecastingService

# Z-scores for common service levels
SERVICE_LEVEL_Z = {
    90: 1.28,
    95: 1.645,
    97: 1.96,
    99: 2.33,
}


class InventoryForecastService:
    """
    Inventory forecasting: per-product demand prediction + safety stock + reorder points.

    Uses the same Holt-Winters engine as the sales forecasting module to predict
    future demand for each product, then calculates inventory requirements.
    """

    def __init__(self, alpha=0.3, beta=0.1, gamma=0.2):
        self.forecasting = ForecastingService(alpha=alpha, beta=beta, gamma=gamma)
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def get_product_daily_demand(self, product_id, days_back=90):
        """
        Get daily quantity sold for a specific product.

        :param product_id: The ID of the product to query.
        :type product_id: int
        :param days_back: Number of past days to retrieve data for.
        :type days_back: int
        :return: A tuple of (date strings, daily demand values), zero-filled.
        :rtype: tuple[list[str], list[float]]
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back - 1)

        qs = (
            OrderItem.objects
            .filter(
                order__created_at__date__gte=start_date,
                order__created_at__date__lte=end_date,
                product_id=product_id,
            )
            .exclude(order__status__in=['cancelled_user', 'cancelled_manager'])
            .annotate(order_date=TruncDate('order__created_at'))
            .values('order_date')
            .annotate(total_qty=Sum('quantity'))
            .order_by('order_date')
        )

        sales_map = {row['order_date']: row['total_qty'] for row in qs}

        dates = []
        values = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime('%Y-%m-%d'))
            values.append(float(sales_map.get(current, 0)))
            current += timedelta(days=1)

        return dates, values

    def get_all_products_demand(self, days_back=90):
        """
        Get aggregated daily demand for all products that have been sold.

        :param days_back: Number of past days to retrieve data for.
        :type days_back: int
        :return: Per-product demand data keyed by product ID.
        :rtype: dict[int, dict]
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back - 1)

        sold_products = (
            OrderItem.objects
            .filter(
                order__created_at__date__gte=start_date,
                order__created_at__date__lte=end_date,
            )
            .exclude(order__status__in=['cancelled_user', 'cancelled_manager'])
            .values('product_id', 'product_name')
            .annotate(total_sold=Sum('quantity'))
            .order_by('-total_sold')
        )

        result = {}
        for item in sold_products:
            pid = item['product_id']
            if pid is None:
                continue
            dates, values = self.get_product_daily_demand(pid, days_back)
            result[pid] = {
                'name': item['product_name'],
                'total_sold': item['total_sold'],
                'dates': dates,
                'values': values,
            }

        return result

    @staticmethod
    def calculate_safety_stock(daily_demand, lead_time, service_level=95):
        """
        Calculate safety stock based on demand variability and service level.

        :param daily_demand: List of daily demand values.
        :type daily_demand: list[float]
        :param lead_time: Supplier lead time in days.
        :type lead_time: int
        :param service_level: Desired service level (90, 95, 97, or 99).
        :type service_level: int
        :return: A tuple of (safety stock, standard deviation of demand).
        :rtype: tuple[float, float]
        """
        z = SERVICE_LEVEL_Z.get(service_level, 1.645)

        if not daily_demand or len(daily_demand) < 2:
            return 0.0, 0.0

        n = len(daily_demand)
        mean = sum(daily_demand) / n
        variance = sum((x - mean) ** 2 for x in daily_demand) / (n - 1)
        std_dev = math.sqrt(variance)

        safety_stock = z * std_dev * math.sqrt(lead_time)
        return round(safety_stock, 1), round(std_dev, 2)

    @staticmethod
    def calculate_reorder_point(avg_daily_demand, lead_time, safety_stock):
        """
        Calculate the inventory reorder point.

        :param avg_daily_demand: Average daily demand.
        :type avg_daily_demand: float
        :param lead_time: Supplier lead time in days.
        :type lead_time: int
        :param safety_stock: Calculated safety stock level.
        :type safety_stock: float
        :return: The reorder point in units.
        :rtype: float
        """
        rop = avg_daily_demand * lead_time + safety_stock
        return round(rop, 1)

    def forecast_product_demand(self, daily_values, forecast_days=14):
        """
        Forecast future demand for a single product.

        Uses Holt-Winters if enough data is available; otherwise
        falls back to Moving Average or simple average.

        :param daily_values: Historical daily demand values.
        :type daily_values: list[float]
        :param forecast_days: Number of days to forecast.
        :type forecast_days: int
        :return: A tuple of (forecast, smoothed, method_name, error_metrics).
        :rtype: tuple[list[float], list[float], str, dict]
        """
        if not daily_values or all(v == 0 for v in daily_values):
            return [0.0] * forecast_days, [], 'no_data', {}

        # Try Holt-Winters first
        min_hw_data = 2 * self.forecasting.SEASON_PERIOD
        if len(daily_values) >= min_hw_data:
            hw_forecast, hw_smoothed = self.forecasting.holt_winters_forecast(
                daily_values, horizon=forecast_days
            )
            # Ensure no negative demand
            hw_forecast = [max(0, v) for v in hw_forecast]

            metrics = {
                'mae': self.forecasting.mae(daily_values, hw_smoothed),
                'rmse': self.forecasting.rmse(daily_values, hw_smoothed),
                'mape': self.forecasting.mape(daily_values, hw_smoothed),
            }
            return hw_forecast, hw_smoothed, 'holt_winters', metrics

        # Fallback: Moving Average
        ma_smoothed = self.forecasting.moving_average(daily_values, window=7)
        ma_forecast = self.forecasting.moving_average_forecast(
            daily_values, window=7, horizon=forecast_days
        )
        ma_forecast = [max(0, v) for v in ma_forecast]

        metrics = {
            'mae': self.forecasting.mae(daily_values, ma_smoothed),
            'rmse': self.forecasting.rmse(daily_values, ma_smoothed),
            'mape': self.forecasting.mape(daily_values, ma_smoothed),
        }
        return ma_forecast, ma_smoothed, 'moving_average', metrics

    def generate_inventory_forecast(self, days_back=90, forecast_days=14,
                                    lead_time=7, service_level=95):
        """
        Generate inventory recommendations for all products.

        :param days_back: Number of historical days to analyze.
        :type days_back: int
        :param forecast_days: Planning horizon in days.
        :type forecast_days: int
        :param lead_time: Supplier lead time in days.
        :type lead_time: int
        :param service_level: Desired service level (90, 95, 97, or 99).
        :type service_level: int
        :return: A dict with 'products', 'summary', and 'params' keys.
        :rtype: dict
        """
        products_demand = self.get_all_products_demand(days_back)

        if not products_demand:
            return {
                'products': [],
                'summary': {'total_products': 0, 'message': 'No sales data available.'},
                'params': self._get_params(days_back, forecast_days, lead_time, service_level),
            }

        products_analysis = []

        for pid, pdata in products_demand.items():
            values = pdata['values']

            # Demand statistics
            avg_daily = sum(values) / len(values) if values else 0
            max_daily = max(values) if values else 0
            days_with_sales = sum(1 for v in values if v > 0)

            # Forecast demand
            forecast, smoothed, method, metrics = self.forecast_product_demand(
                values, forecast_days
            )

            # Safety stock
            safety_stock, demand_std = self.calculate_safety_stock(
                values, lead_time, service_level
            )

            # Reorder point
            reorder_point = self.calculate_reorder_point(avg_daily, lead_time, safety_stock)

            # Recommended order quantity =
            #   total forecasted demand over horizon + safety stock
            forecast_total_demand = sum(forecast)
            recommended_order_qty = math.ceil(forecast_total_demand + safety_stock)

            # Demand trend from forecast
            if len(forecast) >= 2:
                trend = 'growing' if forecast[-1] > forecast[0] * 1.05 else \
                    'declining' if forecast[-1] < forecast[0] * 0.95 else 'stable'
            else:
                trend = 'stable'

            # Demand variability coefficient (CV = σ/μ)
            cv = round(demand_std / avg_daily, 2) if avg_daily > 0 else 0

            # Classify demand pattern
            if cv < 0.5:
                demand_pattern = 'stable'
            elif cv < 1.0:
                demand_pattern = 'variable'
            else:
                demand_pattern = 'highly_variable'

            products_analysis.append({
                'product_id': pid,
                'product_name': pdata['name'],
                'total_sold': pdata['total_sold'],

                # Historical stats
                'avg_daily_demand': round(avg_daily, 2),
                'max_daily_demand': max_daily,
                'demand_std': demand_std,
                'days_with_sales': days_with_sales,
                'total_days': len(values),
                'cv': cv,
                'demand_pattern': demand_pattern,

                # Forecast
                'forecast': [round(v, 1) for v in forecast],
                'forecast_total': round(forecast_total_demand, 1),
                'forecast_avg_daily': round(forecast_total_demand / forecast_days, 2) if forecast_days else 0,
                'forecast_method': method,
                'forecast_metrics': metrics,
                'trend': trend,

                # Inventory recommendations
                'safety_stock': safety_stock,
                'reorder_point': reorder_point,
                'recommended_order_qty': recommended_order_qty,

                # Chart data
                'dates': pdata['dates'],
                'history': values,
                'smoothed': smoothed,
            })

        # Sort by total sold descending
        products_analysis.sort(key=lambda x: x['total_sold'], reverse=True)

        # Summary
        total_recommended = sum(p['recommended_order_qty'] for p in products_analysis)
        growing_count = sum(1 for p in products_analysis if p['trend'] == 'growing')
        declining_count = sum(1 for p in products_analysis if p['trend'] == 'declining')

        summary = {
            'total_products': len(products_analysis),
            'total_recommended_units': total_recommended,
            'growing_products': growing_count,
            'declining_products': declining_count,
            'stable_products': len(products_analysis) - growing_count - declining_count,
            'avg_safety_stock': round(
                sum(p['safety_stock'] for p in products_analysis) / len(products_analysis), 1
            ) if products_analysis else 0,
        }

        return {
            'products': products_analysis,
            'summary': summary,
            'params': self._get_params(days_back, forecast_days, lead_time, service_level),
        }

    def generate_single_product_forecast(self, product_id, days_back=90,
                                         forecast_days=14, lead_time=7,
                                         service_level=95):
        """
        Generate a detailed inventory forecast for a single product.

        :param product_id: The ID of the product to forecast.
        :type product_id: int
        :param days_back: Number of historical days to analyze.
        :type days_back: int
        :param forecast_days: Planning horizon in days.
        :type forecast_days: int
        :param lead_time: Supplier lead time in days.
        :type lead_time: int
        :param service_level: Desired service level (90, 95, 97, or 99).
        :type service_level: int
        :return: Full time series data for charting, or None if no data.
        :rtype: dict or None
        """
        dates, values = self.get_product_daily_demand(product_id, days_back)

        if not values or all(v == 0 for v in values):
            return None

        # Get product name
        try:
            product = Product.objects.get(pk=product_id)
            product_name = product.name
        except Product.DoesNotExist:
            # Try getting from OrderItem
            oi = OrderItem.objects.filter(product_id=product_id).first()
            product_name = oi.product_name if oi else f'Product #{product_id}'

        avg_daily = sum(values) / len(values)
        max_daily = max(values)

        # Forecast
        forecast, smoothed, method, metrics = self.forecast_product_demand(
            values, forecast_days
        )

        # Safety stock
        safety_stock, demand_std = self.calculate_safety_stock(
            values, lead_time, service_level
        )

        # Reorder point
        reorder_point = self.calculate_reorder_point(avg_daily, lead_time, safety_stock)

        # Recommended order qty
        forecast_total = sum(forecast)
        recommended_qty = math.ceil(forecast_total + safety_stock)

        # Forecast dates
        last_date_obj = timezone.now().date()
        forecast_dates = [
            (last_date_obj + timedelta(days=i + 1)).strftime('%Y-%m-%d')
            for i in range(forecast_days)
        ]

        # Demand variability
        cv = round(demand_std / avg_daily, 2) if avg_daily > 0 else 0

        return {
            'product_id': product_id,
            'product_name': product_name,

            # Time series
            'dates': dates,
            'history': values,
            'smoothed': smoothed,
            'forecast': [round(v, 1) for v in forecast],
            'forecast_dates': forecast_dates,
            'forecast_method': method,
            'forecast_metrics': metrics,

            # Statistics
            'avg_daily_demand': round(avg_daily, 2),
            'max_daily_demand': max_daily,
            'demand_std': demand_std,
            'cv': cv,
            'total_sold': sum(values),

            # Inventory recommendations
            'safety_stock': safety_stock,
            'reorder_point': reorder_point,
            'forecast_total_demand': round(forecast_total, 1),
            'recommended_order_qty': recommended_qty,

            'params': self._get_params(days_back, forecast_days, lead_time, service_level),
        }

    def _get_params(self, days_back, forecast_days, lead_time, service_level):
        return {
            'days_back': days_back,
            'forecast_days': forecast_days,
            'lead_time': lead_time,
            'service_level': service_level,
            'alpha': self.alpha,
            'beta': self.beta,
            'gamma': self.gamma,
            'z_score': SERVICE_LEVEL_Z.get(service_level, 1.645),
        }
