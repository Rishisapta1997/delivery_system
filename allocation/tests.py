from django.test import TestCase
from django.utils import timezone
from datetime import date
from decimal import Decimal
from delivery.models import Warehouse, Agent, Order, AgentDailyMetrics
from allocation.allocation_logic import DeliveryAllocationSystem


class AllocationTestCase(TestCase):
    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name="Test Warehouse",
            address="Test Address",
            latitude=Decimal("28.6139"),
            longitude=Decimal("77.2090"),
            capacity=1000
        )
        
        self.agent = Agent.objects.create(
            name="Test Agent",
            warehouse=self.warehouse,
            employee_id="TEST001",
            phone_number="9876543210",
            email="test@test.com",
            is_active=True,
            checkin_time=timezone.now().time()
        )
        
        for i in range(10):
            Order.objects.create(
                order_id=f"TEST00{i}",
                customer_name=f"Customer {i}",
                customer_address=f"Address {i}",
                customer_latitude=Decimal("28.6139") + Decimal(str(i * 0.001)),
                customer_longitude=Decimal("77.2090") + Decimal(str(i * 0.001)),
                warehouse=self.warehouse,
                weight=Decimal("1.0"),
                priority=1,
                status='pending'
            )
    
    def test_allocation_system(self):
        allocator = DeliveryAllocationSystem()
        result = allocator.allocate_orders_to_agents(self.warehouse.id)
        
        self.assertIn('assigned_orders', result)
        self.assertIn('deferred_orders', result)
        
        assigned_orders = Order.objects.filter(
            warehouse=self.warehouse,
            status='assigned'
        ).count()
        
        self.assertEqual(assigned_orders, result['assigned_orders'])
    
    def test_constraints(self):
        allocator = DeliveryAllocationSystem()
        
        metrics = AgentDailyMetrics.objects.create(
            agent=self.agent,
            date=date.today(),
            total_orders=0,
            total_distance=Decimal("99.0"),
            total_working_hours=Decimal("9.8"),
            is_active=True
        )
        
        can_assign, reason = allocator.can_assign_order(
            metrics, 
            distance_to_order=2.0,
            current_orders=0
        )
        
        self.assertFalse(can_assign)
        self.assertEqual(reason, "Distance limit exceeded")
    
    def test_distance_calculation(self):
        allocator = DeliveryAllocationSystem()
        
        distance = allocator.calculate_distance(
            Decimal("28.6139"), Decimal("77.2090"),
            Decimal("28.6239"), Decimal("77.2190")
        )
        
        self.assertGreater(distance, 0)
        self.assertLess(distance, 5)