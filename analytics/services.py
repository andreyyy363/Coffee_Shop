"""
Sales Forecasting Service.

Provides time series analysis and forecasting tools for sales data.
Implements Moving Average, Single Exponential Smoothing, and
Holt-Winters Triple Exponential Smoothing methods.
The primary method is Holt-Winters with additive weekly seasonality.
"""

from datetime import timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from orders.models import Order


class ForecastingService:
    """Sales forecasting using time series analysis."""

    # Default smoothing parameters
    DEFAULT_ALPHA = 0.3  # Level smoothing
    DEFAULT_BETA = 0.1  # Trend smoothing
    DEFAULT_GAMMA = 0.2  # Seasonal smoothing
    SEASON_PERIOD = 7  # Weekly seasonality

    def __init__(self, alpha=None, beta=None, gamma=None):
        self.alpha = alpha or self.DEFAULT_ALPHA
        self.beta = beta or self.DEFAULT_BETA
        self.gamma = gamma or self.DEFAULT_GAMMA

    def get_daily_sales(self, days_back=90):
        """
        Get daily sales aggregation from completed and active orders.

        This method retrieves sales data for the specified number of past days,
        aggregating revenue and order counts by date. It ensures that days with
        no sales are represented with zero values to maintain a continuous time series.

        :param days_back: The number of days in the past to retrieve data for.
        :type days_back: int
        :return: A list of dictionaries containing date, revenue, and order count.
        :rtype: list[dict]
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back - 1)

        # Aggregate orders by day (exclude canceled)
        qs = (
            Order.objects
            .exclude(status__in=['cancelled_user', 'cancelled_manager'])
            .filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
            .annotate(order_date=TruncDate('created_at'))
            .values('order_date')
            .annotate(
                revenue=Sum('total'),
                order_count=Count('id'),
            )
            .order_by('order_date')
        )

        # Build lookup
        sales_map = {}
        for row in qs:
            sales_map[row['order_date']] = {
                'revenue': float(row['revenue']),
                'orders': row['order_count'],
            }

        # Fill gaps with zeros
        result = []
        current = start_date
        while current <= end_date:
            data = sales_map.get(current, {'revenue': 0.0, 'orders': 0})
            result.append({
                'date': current,
                'revenue': data['revenue'],
                'orders': data['orders'],
            })
            current += timedelta(days=1)

        return result

    def get_monthly_sales(self, months_back=12):
        """
        Get monthly sales aggregation.

        This method aggregates sales data by month for the specified number of past months.

        :param months_back: The number of months in the past to retrieve data for.
        :type months_back: int
        :return: A list of dictionaries containing date (month), revenue, and order count.
        :rtype: list[dict]
        """
        from django.db.models.functions import TruncMonth

        end_date = timezone.now().date()
        start_date = end_date.replace(day=1) - timedelta(days=months_back * 30)

        qs = (
            Order.objects
            .exclude(status__in=['cancelled_user', 'cancelled_manager'])
            .filter(created_at__date__gte=start_date)
            .annotate(order_month=TruncMonth('created_at'))
            .values('order_month')
            .annotate(
                revenue=Sum('total'),
                order_count=Count('id'),
            )
            .order_by('order_month')
        )

        return [
            {
                'date': row['order_month'].date() if hasattr(row['order_month'], 'date') else row['order_month'],
                'revenue': float(row['revenue']),
                'orders': row['order_count'],
            }
            for row in qs
        ]

    @staticmethod
    def moving_average(data, window=7):
        """
        Calculate the Simple Moving Average (SMA).

        This process smooths out data by creating a constantly updating average,
        which helps to filter out noise from random short-term fluctuations.

        :param data: The input sequence of numerical values.
        :type data: list[float]
        :param window: The number of data points to include in the average.
        :type window: int
        :return: A list of smoothed values corresponding to the input data.
        :rtype: list[float]
        """
        if len(data) < window:
            return data[:]

        result = [None] * (window - 1)  # Not enough data for first (window-1) points
        for i in range(window - 1, len(data)):
            window_slice = data[i - window + 1:i + 1]
            avg = sum(window_slice) / window
            result.append(round(avg, 2))
        return result

    @staticmethod
    def moving_average_forecast(data, window=7, horizon=14):
        """
        Forecast future values using the Moving Average method.

        This method projects future values by repeating the most recent calculated
        moving average value for the specified forecast horizon.

        :param data: The historical data sequence.
        :type data: list[float]
        :param window: The window size used for the moving average.
        :type window: int
        :param horizon: The number of future time steps to forecast.
        :type horizon: int
        :return: A list of forecasted values.
        :rtype: list[float]
        """
        if len(data) < window:
            last_avg = sum(data) / len(data) if data else 0
        else:
            last_avg = sum(data[-window:]) / window
        return [round(last_avg, 2)] * horizon

    def single_exponential_smoothing(self, data):
        """
        Apply Single Exponential Smoothing (SES) to the data.

        This method smooths time series data using an exponential window function,
        assigning exponentially decreasing weights to data points over time.
        It is suitable for data with no clear trend or seasonality.

        :param data: The input sequence of numerical values.
        :type data: list[float]
        :return: A list of smoothed values.
        :rtype: list[float]
        """
        if not data:
            return []

        result = [data[0]]
        for i in range(1, len(data)):
            s = self.alpha * data[i] + (1 - self.alpha) * result[-1]
            result.append(round(s, 2))
        return result

    def holt_winters(self, data, season_period=None):
        """
        Apply the Holt-Winters Additive method for time series smoothing.

        This method extends exponential smoothing to capture level, trend, and
        seasonality in the data. It decomposes the time series into these three components.
        If there is insufficient data, it falls back to Single Exponential Smoothing.

        :param data: The input sequence of numerical values.
        :type data: list[float]
        :param season_period: The length of the seasonal cycle (e.g., 7 for weekly).
        :type season_period: int or None
        :return: A tuple containing the smoothed values, levels, trends, and seasonal components.
        :rtype: tuple
        """
        m = season_period or self.SEASON_PERIOD
        n = len(data)

        if n < 2 * m:
            # Not enough data for Holt-Winters, fall back to SES
            smoothed = self.single_exponential_smoothing(data)
            return smoothed, None, None, None

        alpha, beta, gamma = self.alpha, self.beta, self.gamma

        # Level: average of first season
        l0 = sum(data[:m]) / m

        # Trend: average difference between first two seasons
        if n >= 2 * m:
            first_season_avg = sum(data[:m]) / m
            second_season_avg = sum(data[m:2 * m]) / m
            b0 = (second_season_avg - first_season_avg) / m
        else:
            b0 = 0.0

        # Seasonal components: deviation from initial level
        season = [data[i] - l0 for i in range(m)]

        levels = [l0]
        trends = [b0]
        seasons = season[:]
        smoothed = [l0 + b0 + season[0]]

        for t in range(1, n):
            if t < m:
                s_prev = season[t]
            else:
                s_prev = seasons[t - m]

            # Level
            l_t = alpha * (data[t] - s_prev) + (1 - alpha) * (levels[-1] + trends[-1])
            # Trend
            b_t = beta * (l_t - levels[-1]) + (1 - beta) * trends[-1]
            # Season
            s_t = gamma * (data[t] - l_t) + (1 - gamma) * s_prev

            levels.append(l_t)
            trends.append(b_t)
            seasons.append(s_t)
            smoothed.append(round(l_t + b_t + s_t, 2))

        return smoothed, levels, trends, seasons

    def holt_winters_forecast(self, data, horizon=14, season_period=None):
        """
        Forecast future values using the Holt-Winters method.

        This method generates future predictions by combining the estimated level,
        trend, and seasonal components derived from the historical data.

        :param data: The historical data sequence.
        :type data: list[float]
        :param horizon: The number of future time steps to forecast.
        :type horizon: int
        :param season_period: The length of the seasonal cycle.
        :type season_period: int or None
        :return: A tuple containing the list of forecasted values and the smoothed history.
        :rtype: tuple[list[float], list[float]]
        """
        m = season_period or self.SEASON_PERIOD
        smoothed, levels, trends, seasons = self.holt_winters(data, m)

        if levels is None:
            # Fallback: no seasonality available
            last_val = smoothed[-1] if smoothed else 0
            return [round(last_val, 2)] * horizon, smoothed

        last_level = levels[-1]
        last_trend = trends[-1]

        forecast = []
        for h in range(1, horizon + 1):
            # Get seasonal component from the last available season
            season_idx = len(seasons) - m + ((h - 1) % m)
            if 0 <= season_idx < len(seasons):
                s = seasons[season_idx]
            else:
                s = 0
            y_hat = last_level + h * last_trend + s
            forecast.append(round(max(y_hat, 0), 2))  # No negative sales

        return forecast, smoothed

    @staticmethod
    def mae(actual, predicted):
        """
        Calculate the Mean Absolute Error (MAE).

        MAE measures the average magnitude of the errors in a set of predictions,
        without considering their direction.

        :param actual: The actual observed values.
        :type actual: list[float]
        :param predicted: The predicted values.
        :type predicted: list[float]
        :return: The mean absolute error.
        :rtype: float
        """
        pairs = [(a, p) for a, p in zip(actual, predicted) if p is not None]
        if not pairs:
            return 0
        return round(sum(abs(a - p) for a, p in pairs) / len(pairs), 2)

    @staticmethod
    def mape(actual, predicted):
        """
        Calculate the Mean Absolute Percentage Error (MAPE).

        MAPE measures the accuracy of a forecast system essentially as a percentage,
        calculated as the average absolute percent error for each time period minus actual values.

        :param actual: The actual observed values.
        :type actual: list[float]
        :param predicted: The predicted values.
        :type predicted: list[float]
        :return: The mean absolute percentage error (in percent).
        :rtype: float
        """
        pairs = [(a, p) for a, p in zip(actual, predicted) if p is not None and a != 0]
        if not pairs:
            return 0
        return round(sum(abs((a - p) / a) for a, p in pairs) / len(pairs) * 100, 1)

    @staticmethod
    def rmse(actual, predicted):
        """
        Calculate the Root Mean Square Error (RMSE).

        RMSE is a quadratic scoring rule that also measures the average magnitude
        of the error. It is the square root of the average of squared differences
        between prediction and actual observation.

        :param actual: The actual observed values.
        :type actual: list[float]
        :param predicted: The predicted values.
        :type predicted: list[float]
        :return: The root mean square error.
        :rtype: float
        """
        pairs = [(a, p) for a, p in zip(actual, predicted) if p is not None]
        if not pairs:
            return 0
        mse = sum((a - p) ** 2 for a, p in pairs) / len(pairs)
        return round(mse ** 0.5, 2)

    def generate_forecast(self, metric='revenue', days_back=90, forecast_days=14):
        """
        Generate a comprehensive sales forecast report.

        This is the main driver method that retrieves historical data, applies
        forecasting models (Moving Average and Holt-Winters), and compiles
        the results along with error metrics and a summary.

        :param metric: The metric to forecast (e.g., 'revenue' or 'orders').
        :type metric: str
        :param days_back: The number of days of history to use.
        :type days_back: int
        :param forecast_days: The number of days to forecast into the future.
        :type forecast_days: int
        :return: A dictionary containing forecast data, metrics, and summary.
        :rtype: dict
        """
        daily = self.get_daily_sales(days_back)

        if not daily:
            return {
                'dates': [],
                'actual': [],
                'hw_smoothed': [],
                'hw_forecast': [],
                'ma_smoothed': [],
                'ma_forecast': [],
                'forecast_dates': [],
                'metrics': {},
                'summary': 'No sales data available.',
            }

        values = [d[metric] for d in daily]
        dates = [d['date'].strftime('%Y-%m-%d') for d in daily]

        # Moving Average
        ma_window = 7
        ma_smoothed = self.moving_average(values, ma_window)
        ma_forecast = self.moving_average_forecast(values, ma_window, forecast_days)

        # Holt-Winters
        hw_forecast, hw_smoothed = self.holt_winters_forecast(
            values, horizon=forecast_days, season_period=7
        )

        # Forecast dates
        last_date = daily[-1]['date']
        forecast_dates = [
            (last_date + timedelta(days=i + 1)).strftime('%Y-%m-%d')
            for i in range(forecast_days)
        ]

        # Error Metrics (on historical data)
        metrics = {
            'moving_average': {
                'mae': self.mae(values, ma_smoothed),
                'rmse': self.rmse(values, ma_smoothed),
                'mape': self.mape(values, ma_smoothed),
            },
            'holt_winters': {
                'mae': self.mae(values, hw_smoothed),
                'rmse': self.rmse(values, hw_smoothed),
                'mape': self.mape(values, hw_smoothed),
            },
        }

        # Summary stats
        non_zero = [v for v in values if v > 0]
        total_revenue = sum(values)
        avg_daily = total_revenue / len(values) if values else 0
        forecast_total = sum(hw_forecast)

        summary = {
            'total_revenue': round(total_revenue, 2),
            'avg_daily': round(avg_daily, 2),
            'days_with_sales': len(non_zero),
            'total_days': len(values),
            'forecast_total': round(forecast_total, 2),
            'forecast_avg_daily': round(forecast_total / forecast_days, 2) if forecast_days else 0,
            'trend': 'up' if hw_forecast[-1] > hw_forecast[0] else 'down' if hw_forecast[-1] < hw_forecast[
                0] else 'stable',
        }

        return {
            'dates': dates,
            'actual': values,
            'hw_smoothed': hw_smoothed,
            'hw_forecast': hw_forecast,
            'ma_smoothed': ma_smoothed,
            'ma_forecast': ma_forecast,
            'forecast_dates': forecast_dates,
            'metrics': metrics,
            'summary': summary,
            'params': {
                'alpha': self.alpha,
                'beta': self.beta,
                'gamma': self.gamma,
                'season_period': self.SEASON_PERIOD,
                'ma_window': ma_window,
            },
        }

    def get_product_sales_ranking(self, days_back=30):
        """Top selling products for the period."""
        from orders.models import OrderItem

        start_date = timezone.now() - timedelta(days=days_back)

        return (
            OrderItem.objects
            .filter(
                order__created_at__gte=start_date,
                order__status__in=['processing', 'packing', 'shipping', 'completed'],
            )
            .values('product_name')
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum('total_price'),
            )
            .order_by('-total_revenue')[:10]
        )
