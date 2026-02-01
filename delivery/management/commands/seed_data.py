from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.db import transaction
from delivery.models import Warehouse, Agent, Order, AgentDailyMetrics, AssignmentLog, DeliveryAttempt
from authentication.models import User
from datetime import datetime, timedelta, date, time
import random
from decimal import Decimal
import uuid


class Command(BaseCommand):
    help = 'Seed COMPLETE realistic test data for delivery system'
    
    def add_arguments(self, parser):
        parser.add_argument('--warehouses', type=int, default=3, help='Number of warehouses')
        parser.add_argument('--agents', type=int, default=20, help='Total agents')
        parser.add_argument('--days', type=int, default=30, help='Number of past days to generate data for')
    
    def handle(self, *args, **kwargs):
        with transaction.atomic():
            self.stdout.write(self.style.WARNING('🚀 Starting COMPLETE data seeding...'))
            
            # 1. Create demo users first
            self.stdout.write('👤 Creating demo users...')
            demo_users = self.create_demo_users()
            
            # 2. Create warehouses
            self.stdout.write('🏢 Creating warehouses...')
            warehouses = self.create_warehouses(kwargs['warehouses'])
            
            # 3. Create agents and link to users
            self.stdout.write('🚚 Creating delivery agents...')
            agents = self.create_agents_with_users(warehouses, kwargs['agents'], demo_users)
            
            # 4. Create realistic orders for past days
            self.stdout.write('📦 Creating orders with realistic timeline...')
            total_orders = self.create_realistic_orders(warehouses, agents, kwargs['days'])
            
            # 5. Create delivery attempts for delivered/deferred orders
            self.stdout.write('📋 Creating delivery attempts...')
            self.create_delivery_attempts()
            
            # 6. Create assignment logs for allocated orders
            self.stdout.write('📝 Creating assignment logs...')
            self.create_assignment_logs(warehouses, agents, kwargs['days'])
            
            # 7. Create agent daily metrics
            self.stdout.write('📊 Creating agent daily metrics...')
            self.create_agent_daily_metrics(agents, kwargs['days'])
            
            # 8. Update today's pending orders for allocation
            self.stdout.write('⏳ Setting up today\'s pending orders...')
            self.setup_todays_orders(warehouses)
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n' + '='*50))
            self.stdout.write(self.style.SUCCESS('✅ SEEDING COMPLETE!'))
            self.stdout.write(self.style.SUCCESS('='*50))
            self.stdout.write(self.style.SUCCESS(f'🏢 Warehouses: {Warehouse.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'👤 Users: {User.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'🚚 Agents: {Agent.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'📦 Orders: {Order.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'📋 Delivery Attempts: {DeliveryAttempt.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'📋 Assignment Logs: {AssignmentLog.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'📊 Agent Metrics: {AgentDailyMetrics.objects.count()}'))
            self.stdout.write(self.style.SUCCESS('='*50))
            
            # Show credentials
            self.stdout.write(self.style.NOTICE('\n🔐 LOGIN CREDENTIALS:'))
            self.stdout.write(self.style.NOTICE('  Email: admin@dms.com | Password: admin123'))
            self.stdout.write(self.style.NOTICE('  Email: manager@dms.com | Password: manager123'))
            self.stdout.write(self.style.NOTICE('  Email: agent1@dms.com | Password: agent123'))
            self.stdout.write(self.style.NOTICE('\n🌐 Access: http://localhost:8000'))
    
    def create_demo_users(self):
        """Create demo users with different roles"""
        users_data = [
            # Admin
            {
                'username': 'admin',
                'email': 'admin@dms.com',
                'password': 'admin123',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'phone_number': '+919876543210'  # Changed from 'phone' to 'phone_number'
            },
            # Delivery Manager
            {
                'username': 'delivery_manager',
                'email': 'manager@dms.com',
                'password': 'manager123',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'role': 'delivery_manager',
                'phone_number': '+919876543211'  # Changed from 'phone' to 'phone_number'
            },
            # Warehouse Manager
            {
                'username': 'warehouse_manager',
                'email': 'warehouse@dms.com',
                'password': 'manager123',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'role': 'warehouse_manager',
                'phone_number': '+919876543212'  # Changed from 'phone' to 'phone_number'
            },
            # Viewer
            {
                'username': 'viewer',
                'email': 'viewer@dms.com',
                'password': 'viewer123',
                'first_name': 'Amit',
                'last_name': 'Verma',
                'role': 'viewer',
                'phone_number': '+919876543213'  # Changed from 'phone' to 'phone_number'
            },
        ]
        
        created_users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'username': user_data['username'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'role': user_data['role'],
                    'phone_number': user_data['phone_number'],  # Changed from 'phone'
                    'is_active': True,
                    'is_staff': user_data['role'] == 'admin',
                    'is_superuser': user_data['role'] == 'admin',
                    'password': make_password(user_data['password'])
                }
            )
            created_users.append(user)
        
        return created_users
    
    def create_warehouses(self, count):
        """Create warehouses in Delhi/NCR area"""
        # Delhi coordinates
        locations = [
            {'name': 'Central Delhi Warehouse', 'area': 'Connaught Place', 'lat': 28.6315, 'lng': 77.2167},
            {'name': 'South Delhi Warehouse', 'area': 'Saket', 'lat': 28.5245, 'lng': 77.2195},
            {'name': 'West Delhi Warehouse', 'area': 'Dwarka', 'lat': 28.5923, 'lng': 77.0497},
            {'name': 'North Delhi Warehouse', 'area': 'Rohini', 'lat': 28.7432, 'lng': 77.0943},
            {'name': 'East Delhi Warehouse', 'area': 'Preet Vihar', 'lat': 28.6361, 'lng': 77.2935},
        ]
        
        warehouses = []
        for i in range(min(count, len(locations))):
            loc = locations[i]
            warehouse, created = Warehouse.objects.get_or_create(
                name=loc['name'],
                defaults={
                    'address': f"{loc['area']}, Delhi, India - 1100{random.randint(10, 99)}",
                    'latitude': Decimal(str(loc['lat'] + random.uniform(-0.01, 0.01))),
                    'longitude': Decimal(str(loc['lng'] + random.uniform(-0.01, 0.01))),
                    'capacity': random.randint(5000, 15000),
                    'created_at': timezone.now() - timedelta(days=random.randint(30, 180))
                }
            )
            warehouses.append(warehouse)
        
        # Create additional warehouses if count > available locations
        for i in range(len(locations), count):
            lat = 28.6139 + random.uniform(-0.2, 0.2)
            lng = 77.2090 + random.uniform(-0.2, 0.2)
            warehouse, created = Warehouse.objects.get_or_create(
                name=f"Warehouse {i+1}",
                defaults={
                    'address': f"Area {i+1}, Delhi, India - 1100{random.randint(10, 99)}",
                    'latitude': Decimal(str(lat)),
                    'longitude': Decimal(str(lng)),
                    'capacity': random.randint(3000, 10000),
                    'created_at': timezone.now() - timedelta(days=random.randint(30, 180))
                }
            )
            warehouses.append(warehouse)
        
        return warehouses
    
    def create_agents_with_users(self, warehouses, total_agents, demo_users):
        """Create agents with linked user accounts"""
        first_names = ['Raj', 'Amit', 'Sanjay', 'Vikram', 'Anil', 'Rahul', 'Suresh', 'Deepak', 'Manoj', 'Sunil',
                      'Priya', 'Anjali', 'Neha', 'Sonia', 'Ritu', 'Pooja', 'Kavita', 'Meera', 'Shweta', 'Divya']
        last_names = ['Sharma', 'Verma', 'Gupta', 'Singh', 'Kumar', 'Yadav', 'Patel', 'Jain', 'Malhotra', 'Reddy',
                     'Choudhary', 'Mishra', 'Tiwari', 'Nair', 'Menon', 'Pillai', 'Naidu', 'Rao', 'Shetty', 'Agarwal']
        
        agents = []
        
        # First create agent users
        agent_users = []
        for i in range(total_agents):
            first = random.choice(first_names)
            last = random.choice(last_names)
            username = f"{first.lower()}{last.lower()}{i}"
            email = f"{username}@dms.com"
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first,
                    'last_name': last,
                    'role': 'agent',
                    'phone_number': f"+919{random.randint(100000000, 999999999)}",
                    'is_active': True,
                    'password': make_password('agent123')
                }
            )
            agent_users.append(user)
        
        # Assign agents to warehouses
        for i, user in enumerate(agent_users):
            warehouse = random.choice(warehouses)
            
            agent, created = Agent.objects.get_or_create(
                user=user,
                defaults={
                    'name': f"{user.first_name} {user.last_name}",
                    'warehouse': warehouse,
                    'employee_id': f"EMP{warehouse.id:02d}{i+1:03d}",
                    'phone_number': user.phone_number,
                    'email': user.email,
                    'is_active': random.choices([True, False], weights=[0.85, 0.15])[0],
                    'created_at': timezone.now() - timedelta(days=random.randint(1, 90))
                }
            )
            
            # Set checkin time for active agents (70% chance)
            if agent.is_active and random.random() > 0.3:
                checkin_hour = random.randint(8, 10)
                checkin_minute = random.randint(0, 59)
                agent.checkin_time = time(checkin_hour, checkin_minute)
                agent.save()
            
            agents.append(agent)
        
        return agents
    
    def create_realistic_orders(self, warehouses, agents, days_back):
        """Create orders with realistic timeline and status progression"""
        today = date.today()
        
        # Areas in Delhi for realistic addresses
        areas = {
            'Central': ['Connaught Place', 'Karol Bagh', 'Paharganj', 'Chanakyapuri'],
            'South': ['Saket', 'Hauz Khas', 'Greater Kailash', 'Defence Colony', 'Malviya Nagar'],
            'West': ['Dwarka', 'Janakpuri', 'Rajouri Garden', 'Pitampura'],
            'North': ['Rohini', 'Model Town', 'Kashmere Gate', 'Civil Lines'],
            'East': ['Preet Vihar', 'Mayur Vihar', 'Laxmi Nagar', 'Geeta Colony']
        }
        
        streets = ['Main Road', 'MG Road', 'Market Street', 'Station Road', 'Park Street',
                  'Club Road', 'School Lane', 'Hospital Road', 'Mall Road', 'Golf Course Road']
        
        # Customer names
        customers = [
            'Aarav Sharma', 'Vivaan Patel', 'Aditya Singh', 'Vihaan Kumar', 'Arjun Gupta',
            'Sai Verma', 'Reyansh Reddy', 'Mohammed Khan', 'Ishaan Joshi', 'Kabir Malhotra',
            'Ananya Reddy', 'Diya Patel', 'Aadhya Singh', 'Ishita Sharma', 'Myra Kumar',
            'Sara Verma', 'Anvi Gupta', 'Kiara Malhotra', 'Riya Joshi', 'Sana Khan'
        ]
        
        # Product types with weight ranges
        products = [
            ('Electronics', 0.5, 5.0),
            ('Clothing', 0.2, 2.0),
            ('Groceries', 1.0, 10.0),
            ('Books', 0.3, 3.0),
            ('Medicines', 0.1, 1.0),
            ('Furniture', 5.0, 25.0),
            ('Toys', 0.5, 3.0),
            ('Cosmetics', 0.2, 1.5)
        ]
        
        total_orders = 0
        
        # Create orders for each day in the past
        for day_offset in range(days_back, -1, -1):  # From oldest to newest
            order_date = today - timedelta(days=day_offset)
            
            # Different order volume based on day type
            if order_date.weekday() in [5, 6]:  # Weekend
                orders_per_warehouse = random.randint(15, 25)
            else:  # Weekday
                orders_per_warehouse = random.randint(25, 40)
            
            # Time distribution: 70% in morning, 30% in afternoon
            morning_hours = [8, 9, 10, 11]
            afternoon_hours = [12, 13, 14, 15, 16]
            
            for warehouse in warehouses:
                # Get active agents from this warehouse
                warehouse_agents = [a for a in agents if a.warehouse == warehouse and a.is_active]
                if not warehouse_agents:
                    continue
                
                # Determine area based on warehouse location
                if 'Central' in warehouse.name:
                    area_type = 'Central'
                elif 'South' in warehouse.name:
                    area_type = 'South'
                elif 'West' in warehouse.name:
                    area_type = 'West'
                elif 'North' in warehouse.name:
                    area_type = 'North'
                else:
                    area_type = 'East'
                
                for _ in range(orders_per_warehouse):
                    # Generate customer location near warehouse
                    base_lat = float(warehouse.latitude)
                    base_lng = float(warehouse.longitude)
                    
                    # Most deliveries within 10km radius
                    cust_lat = base_lat + random.uniform(-0.09, 0.09)  # ~10km
                    cust_lng = base_lng + random.uniform(-0.09, 0.09)
                    
                    # Select product type
                    product_type, min_weight, max_weight = random.choice(products)
                    weight = Decimal(str(round(random.uniform(min_weight, max_weight), 2)))
                    
                    # Generate order time
                    if random.random() < 0.7:  # 70% morning orders
                        order_hour = random.choice(morning_hours)
                    else:  # 30% afternoon orders
                        order_hour = random.choice(afternoon_hours)
                    
                    order_minute = random.randint(0, 59)
                    order_datetime = timezone.make_aware(
                        datetime.combine(order_date, time(order_hour, order_minute))
                    )
                    
                    # Determine order status based on date
                    status = self.determine_order_status(order_date, day_offset)
                    
                    # Select agent for assigned/delivered orders
                    assigned_agent = None
                    delivery_date = None
                    
                    if status in ['assigned', 'in_transit', 'delivered', 'deferred']:
                        assigned_agent = random.choice(warehouse_agents)
                        if status in ['delivered', 'deferred']:
                            # Add delivery date (1-3 days after order date)
                            delivery_days = random.randint(1, 3)
                            delivery_date = order_date + timedelta(days=delivery_days)
                    
                    # Create order
                    order = Order.objects.create(
                        order_id=f"ORD{order_date.strftime('%y%m%d')}{warehouse.id:02d}{total_orders+1:04d}",
                        customer_name=random.choice(customers),
                        customer_address=f"{random.randint(1, 999)}, {random.choice(areas[area_type])}, {random.choice(streets)}, Delhi - 1100{random.randint(10, 99)}",
                        customer_latitude=Decimal(str(round(cust_lat, 6))),
                        customer_longitude=Decimal(str(round(cust_lng, 6))),
                        warehouse=warehouse,
                        weight=weight,
                        priority=random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.1, 0.15, 0.3, 0.4])[0],
                        status=status,
                        created_date=order_date,
                        delivery_date=delivery_date,
                        assigned_to=assigned_agent
                    )
                    
                    total_orders += 1
        
        return total_orders
    
    def determine_order_status(self, order_date, day_offset):
        """Determine realistic order status based on date"""
        today = date.today()
        days_ago = (today - order_date).days
        
        if days_ago == 0:  # Today's orders
            return random.choices(
                ['pending', 'pending', 'pending', 'assigned'],
                weights=[0.6, 0.6, 0.6, 0.2]
            )[0]
        elif days_ago == 1:  # Yesterday's orders
            return random.choices(
                ['assigned', 'in_transit', 'delivered', 'deferred'],
                weights=[0.1, 0.3, 0.5, 0.1]
            )[0]
        elif days_ago == 2:  # Day before yesterday
            return random.choices(
                ['delivered', 'deferred', 'in_transit'],
                weights=[0.8, 0.15, 0.05]
            )[0]
        elif days_ago >= 3:  # Older orders
            return random.choices(
                ['delivered', 'deferred'],
                weights=[0.9, 0.1]
            )[0]
        
        return 'pending'
    
    def create_delivery_attempts(self):
        """Create delivery attempts for delivered/deferred orders"""
        # Get orders that need delivery attempts
        orders = Order.objects.filter(
            status__in=['delivered', 'deferred']
        ).exclude(assigned_to=None)
        
        attempt_notes = {
            'successful': [
                "Delivered successfully",
                "Handed over to customer",
                "Left with security",
                "Delivered to reception",
                "Customer signed for delivery"
            ],
            'failed': [
                "Customer not available",
                "Address incorrect",
                "Customer refused delivery",
                "Package damaged",
                "Security denied entry"
            ],
            'rescheduled': [
                "Customer requested reschedule",
                "Bad weather conditions",
                "Vehicle breakdown",
                "Customer on vacation",
                "Address not found"
            ]
        }
        
        for order in orders:
            # Number of attempts based on status
            if order.status == 'delivered':
                attempts_count = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
                # Last attempt must be successful
                final_status = 'successful'
            else:  # deferred
                attempts_count = random.choices([2, 3, 4], weights=[0.5, 0.3, 0.2])[0]
                final_status = 'failed'  # All attempts failed
            
            # Calculate attempt times
            if order.delivery_date:
                first_attempt_date = order.delivery_date
            else:
                first_attempt_date = order.created_date + timedelta(days=1)
            
            for attempt_num in range(attempts_count):
                # Determine attempt time
                attempt_hour = random.randint(10, 18)
                attempt_minute = random.randint(0, 59)
                attempt_date = first_attempt_date + timedelta(days=attempt_num)
                attempted_at = timezone.make_aware(
                    datetime.combine(attempt_date, time(attempt_hour, attempt_minute))
                )
                
                # Determine status for this attempt
                if order.status == 'delivered' and attempt_num == attempts_count - 1:
                    status = 'successful'
                    notes = random.choice(attempt_notes['successful'])
                elif order.status == 'deferred':
                    status = random.choice(['failed', 'rescheduled'])
                    notes = random.choice(attempt_notes[status])
                else:
                    status = 'failed'
                    notes = random.choice(attempt_notes['failed'])
                
                DeliveryAttempt.objects.create(
                    order=order,
                    agent=order.assigned_to,
                    attempt_number=attempt_num + 1,
                    attempted_at=attempted_at,
                    status=status,
                    notes=notes,
                    latitude=order.customer_latitude + Decimal(str(random.uniform(-0.001, 0.001))),
                    longitude=order.customer_longitude + Decimal(str(random.uniform(-0.001, 0.001)))
                )
    
    def create_assignment_logs(self, warehouses, agents, days_back):
        """Create assignment logs for allocated orders"""
        today = date.today()
        
        for day_offset in range(days_back, -1, -1):
            assignment_date = today - timedelta(days=day_offset)
            
            # Get orders assigned on this date
            orders = Order.objects.filter(
                status__in=['assigned', 'in_transit', 'delivered', 'deferred'],
                created_date=assignment_date
            ).exclude(assigned_to=None)
            
            for order in orders:
                # Calculate distance (simulated)
                distance = Decimal(str(round(random.uniform(2.0, 15.0), 2)))
                estimated_time = random.randint(30, 120)  # 30-120 minutes
                
                AssignmentLog.objects.get_or_create(
                    agent=order.assigned_to,
                    order=order,
                    assignment_date=assignment_date,
                    defaults={
                        'distance_from_warehouse': distance,
                        'estimated_delivery_time': estimated_time,
                        'assigned_at': timezone.make_aware(
                            datetime.combine(assignment_date, time(9, 0))  # 9 AM assignment
                        )
                    }
                )
    
    def create_agent_daily_metrics(self, agents, days_back):
        """Create daily metrics for agents"""
        today = date.today()
        
        for day_offset in range(days_back, -1, -1):
            metric_date = today - timedelta(days=day_offset)
            
            for agent in agents:
                if not agent.is_active:
                    continue
                
                # Skip weekends for some agents
                if metric_date.weekday() in [5, 6] and random.random() > 0.3:
                    continue
                
                # Get orders delivered by this agent on this date
                delivered_orders = Order.objects.filter(
                    assigned_to=agent,
                    delivery_date=metric_date,
                    status='delivered'
                )
                
                assigned_orders = Order.objects.filter(
                    assigned_to=agent,
                    created_date=metric_date,
                    status__in=['assigned', 'in_transit', 'delivered', 'deferred']
                )
                
                if delivered_orders.exists() or assigned_orders.exists():
                    total_orders = delivered_orders.count()
                    total_distance = Decimal(str(round(random.uniform(20.0, 80.0), 2)))
                    total_hours = Decimal(str(round(random.uniform(4.0, 10.0), 1)))
                    
                    AgentDailyMetrics.objects.get_or_create(
                        agent=agent,
                        date=metric_date,
                        defaults={
                            'total_orders': total_orders,
                            'orders_assigned': assigned_orders.count(),
                            'orders_delivered': delivered_orders.count(),
                            'total_distance': total_distance,
                            'total_working_hours': total_hours,
                            'is_active': True
                        }
                    )
    
    def setup_todays_orders(self, warehouses):
        """Set up realistic pending orders for today"""
        today = date.today()
        
        # Areas in Delhi
        areas = ['Connaught Place', 'Saket', 'Dwarka', 'Rohini', 'Preet Vihar']
        streets = ['MG Road', 'Market Street', 'Station Road', 'Park Street']
        customers = ['Online Shopper', 'Corporate Client', 'Regular Customer', 'New Customer']
        
        # Create fresh pending orders for today
        for warehouse in warehouses:
            # 10-20 pending orders per warehouse for today
            pending_count = random.randint(10, 20)
            
            for i in range(pending_count):
                # Generate customer location
                base_lat = float(warehouse.latitude)
                base_lng = float(warehouse.longitude)
                cust_lat = base_lat + random.uniform(-0.05, 0.05)
                cust_lng = base_lng + random.uniform(-0.05, 0.05)
                
                # Create order time for today (morning hours)
                order_hour = random.randint(8, 12)
                order_minute = random.randint(0, 59)
                order_datetime = timezone.make_aware(
                    datetime.combine(today, time(order_hour, order_minute))
                )
                
                Order.objects.create(
                    order_id=f"ORD{today.strftime('%y%m%d')}{warehouse.id:02d}P{i+1:03d}",
                    customer_name=random.choice(customers),
                    customer_address=f"{random.randint(1, 999)}, {random.choice(areas)}, {random.choice(streets)}, Delhi",
                    customer_latitude=Decimal(str(round(cust_lat, 6))),
                    customer_longitude=Decimal(str(round(cust_lng, 6))),
                    warehouse=warehouse,
                    weight=Decimal(str(round(random.uniform(0.5, 8.0), 2))),
                    priority=random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.1, 0.2, 0.3, 0.35])[0],
                    status='pending',  # These will be allocated by the system
                    created_date=today
                )