from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('warehouse_manager', 'Warehouse Manager'),
        ('delivery_manager', 'Delivery Manager'),
        ('agent', 'Delivery Agent'),
        ('viewer', 'Viewer'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    warehouse = models.ForeignKey('delivery.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_warehouse_manager(self):
        return self.role == 'warehouse_manager'
    
    def is_delivery_manager(self):
        return self.role == 'delivery_manager'
    
    def is_agent(self):
        return self.role == 'agent'
    
    def can_manage_warehouse(self, warehouse_id=None):
        if self.is_admin():
            return True
        if self.is_warehouse_manager() and self.warehouse_id == warehouse_id:
            return True
        return False
    
    def can_view_reports(self):
        return self.role in ['admin', 'delivery_manager', 'warehouse_manager']
    
    def can_manage_agents(self):
        return self.role in ['admin', 'delivery_manager']
    
    def can_allocate_orders(self):
        return self.role in ['admin', 'delivery_manager']