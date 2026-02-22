from . import views
from django.urls import path

app_name = 'orders'

urlpatterns = [
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/promo-code/', views.apply_promo_code, name='apply_promo_code'),

    # Orders
    path('', views.orders_list, name='list'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
    path('<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),

    # Manager
    path('manager/orders/', views.manager_orders, name='manager_orders'),
    path('manager/orders/<str:order_number>/', views.manager_order_detail, name='manager_order_detail'),
]
