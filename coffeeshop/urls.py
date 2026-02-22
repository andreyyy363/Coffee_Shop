"""
URL configuration for coffeeshop project.
"""
from . import views
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('contacts/', views.contacts, name='contacts'),
    path('manager/contacts/', views.manager_contact_messages, name='manager_contact_messages'),
    path('manager/contacts/<int:pk>/', views.manager_contact_message_detail, name='manager_contact_message_detail'),
    path('manager/contacts/<int:pk>/delete/', views.manager_contact_message_delete, name='manager_contact_message_delete'),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
    path('reviews/', include('reviews.urls')),
    path('discounts/', include('discounts.urls')),
    path('analytics/', include('analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
