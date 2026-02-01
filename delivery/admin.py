# delivery/admin.py
from django.contrib import admin
from .models import Warehouse, Agent, Order, AgentDailyMetrics, AssignmentLog, DeliveryAttempt


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'latitude', 'longitude', 'capacity']
    search_fields = ['name', 'address']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'employee_id', 'warehouse', 'is_active', 'checkin_time']
    list_filter = ['warehouse', 'is_active']
    search_fields = ['name', 'employee_id', 'email']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer_name', 'warehouse', 'status', 'assigned_to', 'delivery_date']
    list_filter = ['status', 'warehouse', 'delivery_date']
    search_fields = ['order_id', 'customer_name']
    actions = ['mark_as_pending', 'mark_as_deferred']
    
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
    mark_as_pending.short_description = "Mark selected orders as pending"
    
    def mark_as_deferred(self, request, queryset):
        queryset.update(status='deferred')
    mark_as_deferred.short_description = "Mark selected orders as deferred"


@admin.register(AgentDailyMetrics)
class AgentDailyMetricsAdmin(admin.ModelAdmin):
    list_display = ['agent', 'date', 'total_orders', 'total_distance', 'total_working_hours', 'total_earnings']
    list_filter = ['date', 'agent__warehouse']
    readonly_fields = ['total_earnings']


@admin.register(AssignmentLog)
class AssignmentLogAdmin(admin.ModelAdmin):
    list_display = ['agent', 'order', 'assignment_date', 'distance_from_warehouse', 'estimated_delivery_time']
    list_filter = ['assignment_date', 'agent__warehouse']
    search_fields = ['agent__name', 'order__order_id']

@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = ('order', 'attempt_number', 'agent', 'status', 'attempted_at')
    list_filter = ('status', 'attempted_at', 'agent')
    search_fields = ('order__order_id', 'agent__name', 'notes')
    readonly_fields = ('attempted_at', 'created_at')
    ordering = ('-attempted_at',)