from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from delivery.models import Warehouse

User = get_user_model()

class Command(BaseCommand):
    help = 'Create demo users for testing'
    
    def handle(self, *args, **kwargs):
        # Get or create a warehouse
        warehouse, created = Warehouse.objects.get_or_create(
            name="Main Warehouse",
            defaults={
                'address': "123 Main St, City",
                'latitude': '28.6139',
                'longitude': '77.2090',
                'capacity': 5000
            }
        )
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@delivery.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'is_verified': True
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        
        # Create delivery manager
        manager_user, created = User.objects.get_or_create(
            username='manager',
            defaults={
                'email': 'manager@delivery.com',
                'first_name': 'Delivery',
                'last_name': 'Manager',
                'role': 'delivery_manager',
                'is_staff': True,
                'is_active': True,
                'is_verified': True
            }
        )
        manager_user.set_password('manager123')
        manager_user.save()
        
        # Create warehouse manager
        warehouse_manager, created = User.objects.get_or_create(
            username='warehouse',
            defaults={
                'email': 'warehouse@delivery.com',
                'first_name': 'Warehouse',
                'last_name': 'Manager',
                'role': 'warehouse_manager',
                'warehouse': warehouse,
                'is_active': True,
                'is_verified': True
            }
        )
        warehouse_manager.set_password('warehouse123')
        warehouse_manager.save()
        
        # Create agent user
        agent_user, created = User.objects.get_or_create(
            username='agent',
            defaults={
                'email': 'agent@delivery.com',
                'first_name': 'Delivery',
                'last_name': 'Agent',
                'role': 'agent',
                'warehouse': warehouse,
                'is_active': True,
                'is_verified': True
            }
        )
        agent_user.set_password('agent123')
        agent_user.save()
        
        # Create viewer user
        viewer_user, created = User.objects.get_or_create(
            username='viewer',
            defaults={
                'email': 'viewer@delivery.com',
                'first_name': 'System',
                'last_name': 'Viewer',
                'role': 'viewer',
                'is_active': True,
                'is_verified': True
            }
        )
        viewer_user.set_password('viewer123')
        viewer_user.save()
        
        self.stdout.write(self.style.SUCCESS('Demo users created successfully!'))
        self.stdout.write('=' * 50)
        self.stdout.write('Login Credentials:')
        self.stdout.write('Admin: admin / admin123')
        self.stdout.write('Delivery Manager: manager / manager123')
        self.stdout.write('Warehouse Manager: warehouse / warehouse123')
        self.stdout.write('Delivery Agent: agent / agent123')
        self.stdout.write('Viewer: viewer / viewer123')