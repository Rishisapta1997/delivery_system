# delivery/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator, MaxValueValidator


class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    capacity = models.IntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name}"


class Agent(models.Model):
    user = models.OneToOneField('authentication.User', on_delete=models.CASCADE, null=True, blank=True, related_name='agent_profile')
    name = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='agents')
    employee_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    checkin_time = models.TimeField(null=True, blank=True)
    checkout_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['warehouse']),
            models.Index(fields=['is_active']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-create user if not exists
        if not self.user and self.email:
            from authentication.models import User
            user, created = User.objects.get_or_create(
                username=self.employee_id,
                defaults={
                    'email': self.email,
                    'first_name': self.name.split()[0] if self.name else '',
                    'last_name': ' '.join(self.name.split()[1:]) if len(self.name.split()) > 1 else '',
                    'role': 'agent',
                    'phone_number': self.phone_number,
                    'warehouse': self.warehouse,
                    'is_active': self.is_active
                }
            )
            self.user = user
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('deferred', 'Deferred'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_id = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=100)
    customer_address = models.TextField()
    customer_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    customer_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='orders')
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    priority = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    created_date = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_date']),
            models.Index(fields=['warehouse', 'status']),
            models.Index(fields=['assigned_to', 'delivery_date']),
        ]
    
    def __str__(self):
        return f"Order {self.order_id} - {self.customer_name}"


class AgentDailyMetrics(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='daily_metrics')
    date = models.DateField()
    total_orders = models.IntegerField(default=0)
    total_distance = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in km
    total_working_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)  # in hours
    total_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    orders_assigned = models.IntegerField(default=0)
    orders_delivered = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['agent', 'date']
        indexes = [
            models.Index(fields=['date', 'is_active']),
        ]
    
    def calculate_earnings(self):
        if self.total_orders >= 50:
            return self.total_orders * 42
        elif self.total_orders >= 25:
            return self.total_orders * 35
        else:
            # Ensure minimum ₹500
            base_earning = self.total_orders * 20  # Base rate
            return max(base_earning, 500)
    
    def save(self, *args, **kwargs):
        self.total_earnings = self.calculate_earnings()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.agent.name} - {self.date}"


class AssignmentLog(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assignment_date = models.DateField()
    distance_from_warehouse = models.DecimalField(max_digits=6, decimal_places=2)  # in km
    estimated_delivery_time = models.IntegerField()  # in minutes
    
    class Meta:
        indexes = [
            models.Index(fields=['assignment_date', 'agent']),
        ]
        unique_together = ['agent', 'order', 'assignment_date']
    
    def __str__(self):
        return f"{self.agent.name} assigned {self.order.order_id} on {self.assignment_date}"
    
class DeliveryAttempt(models.Model):
    ATTEMPT_STATUS = [
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='delivery_attempts')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='delivery_attempts')
    attempt_number = models.IntegerField(default=1)
    attempted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ATTEMPT_STATUS, default='failed')
    notes = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    photo_url = models.URLField(blank=True)
    signature_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['order', 'attempt_number']),
            models.Index(fields=['attempted_at']),
            models.Index(fields=['agent', 'attempted_at']),
        ]
    
    def __str__(self):
        return f"Attempt {self.attempt_number} for Order {self.order.order_id}"