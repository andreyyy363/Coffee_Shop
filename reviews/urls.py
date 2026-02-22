from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('add/<int:product_id>/', views.add_review, name='add'),
    path('update/<int:review_id>/', views.update_review, name='update'),
    path('delete/<int:review_id>/', views.delete_review, name='delete'),

    # Manager
    path('manager/', views.manager_reviews, name='manager_reviews'),
    path('manager/toggle/<int:review_id>/', views.toggle_review_approval, name='toggle_approval'),
]
