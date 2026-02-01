from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views
from .api_views import assign_order, update_order_status, checkin_agent

urlpatterns = [
    # Authentication URLs
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(next_page='/accounts/login/'), name='logout'),
    
    # Main application URLs
    path('', views.dashboard, name='dashboard'),
    path('orders/', views.orders_view, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('agents/', views.agents_view, name='agents'),
    path('agents/<int:agent_id>/', views.agent_detail, name='agent_detail'),
    path('warehouses/', views.warehouses_view, name='warehouses'),
    path('allocation/', views.allocation_view, name='allocation'),
    path('reports/', views.reports_view, name='reports'),
    path('automation/', views.automation_view, name='automation'),
    
    # API URLs
    path('api/allocation/start/', views.start_allocation, name='start_allocation'),
    path('api/service/start/', views.start_service, name='start_service'),
    path('api/service/stop/', views.stop_service, name='stop_service'),
    path('api/order/<int:order_id>/assign/', assign_order, name='assign_order'),
    path('api/order/<int:order_id>/status/', update_order_status, name='update_order_status'),
    path('api/agent/<int:agent_id>/checkin/', checkin_agent, name='checkin_agent'),
    path('order/<int:order_id>/attempts/', views.delivery_attempt_list, name='delivery_attempts'),
    path('order/<int:order_id>/attempt/create/', views.create_delivery_attempt, name='create_delivery_attempt'),
    path('api/delivery-attempt/create/', views.api_create_delivery_attempt, name='api_create_delivery_attempt'),

]