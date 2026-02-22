from . import views
from django.urls import path

app_name = 'discounts'

urlpatterns = [
    # User views
    path('my-discount/', views.my_discount_view, name='my_discount'),

    # AJAX endpoints
    path('validate-promo/', views.validate_promo_code_ajax, name='validate_promo'),
    path('calculate/', views.calculate_discount_ajax, name='calculate'),

    # Manager views
    path('manager/settings/', views.manager_discount_settings, name='manager_settings'),
    path('manager/promo-codes/', views.manager_promo_codes, name='manager_promo_codes'),
    path('manager/customers/', views.manager_customer_discounts, name='manager_customers'),
    path('manager/recommendations/', views.manager_recommendation_settings, name='manager_recommendations'),
]
