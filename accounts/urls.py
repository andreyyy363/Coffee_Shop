from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:email>/', views.reset_password, name='reset_password'),
    path('settings/', views.account_settings, name='settings'),
]
