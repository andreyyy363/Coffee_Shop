from . import views
from django.urls import path

app_name = 'products'

urlpatterns = [
    path('', views.catalog_view, name='catalog'),
    path('search/', views.search_products, name='search'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),

    # Manager URLs
    path('manager/', views.manager_products, name='manager_products'),
    path('manager/create/', views.manager_product_create, name='manager_product_create'),
    path('manager/<int:pk>/edit/', views.manager_product_edit, name='manager_product_edit'),
    path('manager/<int:pk>/delete/', views.manager_product_delete, name='manager_product_delete'),
    path('manager/<int:pk>/toggle/', views.manager_product_toggle, name='manager_product_toggle'),

    # Reference data management
    path('manager/countries/', views.manager_countries, name='manager_countries'),
    path('manager/roast-levels/', views.manager_roast_levels, name='manager_roast_levels'),
    path('manager/bean-types/', views.manager_bean_types, name='manager_bean_types'),
    path('manager/weights/', views.manager_weights, name='manager_weights'),

    # Product detail (must be last due to slug pattern)
    path('<slug:slug>/', views.product_detail, name='detail'),
]
