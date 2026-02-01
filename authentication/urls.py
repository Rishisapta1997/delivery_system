from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, UserProfileView,
    ChangePasswordView, UpdateProfileView,
    LoginTemplateView, RegisterTemplateView, ForgotPasswordTemplateView
)

urlpatterns = [
    # API Endpoints
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/profile/', UserProfileView.as_view(), name='profile'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('api/update-profile/', UpdateProfileView.as_view(), name='update_profile'),
    
    # Template Views
    path('login/', LoginTemplateView.as_view(), name='login_page'),
    path('register/', RegisterTemplateView.as_view(), name='register_page'),
    path('forgot-password/', ForgotPasswordTemplateView.as_view(), name='forgot_password_page'),
]