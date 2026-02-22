from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('forecast/', views.sales_forecast, name='forecast'),
    path('forecast/api/', views.forecast_api, name='forecast_api'),
    path('inventory/', views.inventory_forecast, name='inventory_forecast'),
    path('inventory/api/', views.inventory_forecast_api, name='inventory_forecast_api'),
    path('inventory/product/<int:product_id>/api/', views.inventory_product_detail_api, name='inventory_product_api'),
]
