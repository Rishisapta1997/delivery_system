from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json

from .models import Warehouse, Agent, Order, AgentDailyMetrics, AssignmentLog, DeliveryAttempt
from allocation.utils import get_daily_summary
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce, NullIf
from django.db.models import DecimalField
from authentication.decorators import role_required
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt


@login_required
@role_required(['admin', 'delivery_manager', 'warehouse_manager', 'agent', 'viewer'])
def dashboard(request):
    today = date.today()
    user = request.user

    # total_warehouses = Warehouse.objects.count()
    # total_agents = Agent.objects.filter(is_active=True).count()
    # total_orders_today = Order.objects.filter(created_date=today).count()


    # checked_in_agents = Agent.objects.filter(
    #     is_active=True,
    #     checkin_time__isnull=False
    # ).count()
    
    # Role-based data filtering
    if user.role == 'admin':
        # Admin sees everything
        total_warehouses = Warehouse.objects.count()
        total_agents = Agent.objects.filter(is_active=True).count()
        total_orders_today = Order.objects.filter(created_date=today).count()
        checked_in_agents = Agent.objects.filter(
            is_active=True,
            checkin_time__isnull=False
        ).count()
        
    elif user.role == 'warehouse_manager':
        # Warehouse manager sees only their warehouse
        warehouse = user.warehouse
        total_warehouses = 1
        total_agents = Agent.objects.filter(warehouse=warehouse, is_active=True).count()
        total_orders_today = Order.objects.filter(warehouse=warehouse, created_date=today).count()
        checked_in_agents = Agent.objects.filter(
            warehouse=warehouse,
            is_active=True,
            checkin_time__isnull=False
        ).count()
        
    elif user.role == 'agent':
        # Agent sees only their data
        agent = Agent.objects.filter(user=user).first()
        total_warehouses = 1
        total_agents = 1
        total_orders_today = Order.objects.filter(assigned_to=agent, created_date=today).count()
        checked_in_agents = 1 if agent and agent.checkin_time else 0
        
    else:
        # Viewer sees limited data
        total_warehouses = Warehouse.objects.count()
        total_agents = Agent.objects.filter(is_active=True).count()
        total_orders_today = Order.objects.filter(created_date=today).count()
        checked_in_agents = Agent.objects.filter(
            is_active=True,
            checkin_time__isnull=False
        ).count()
    
    order_status = Order.objects.filter(created_date=today).values('status').annotate(
        count=Count('id')
    )
    
    daily_summary = get_daily_summary(today)
    
    recent_assignments = AssignmentLog.objects.select_related(
        'agent', 'order'
    ).order_by('-assigned_at')[:10]
    
    top_agents = AgentDailyMetrics.objects.filter(
        date=today,
        total_orders__gt=0
    ).select_related('agent').order_by('-total_orders')[:5]
    
    warehouse_stats = Warehouse.objects.annotate(
        agent_count=Count('agents', filter=Q(agents__is_active=True)),
        order_count=Count('orders', filter=Q(orders__created_date=today)),
        assigned_orders=Count('orders', filter=Q(orders__status='assigned') & Q(orders__created_date=today))
    ).values('name', 'agent_count', 'order_count', 'assigned_orders')
    
    status_data = {item['status']: item['count'] for item in order_status}
    
    context = {
        'page_title': 'Dashboard',
        'total_warehouses': total_warehouses,
        'total_agents': total_agents,
        'total_orders_today': total_orders_today,
        'checked_in_agents': checked_in_agents,
        'order_status': order_status,
        'status_data': json.dumps(status_data),
        'daily_summary': daily_summary,
        'recent_assignments': recent_assignments,
        'top_agents': top_agents,
        'warehouse_stats': warehouse_stats,
        'today': today.strftime('%B %d, %Y'),
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def orders_view(request):
    status_filter = request.GET.get('status', 'all')
    warehouse_filter = request.GET.get('warehouse', 'all')
    date_filter = request.GET.get('date', 'today')
    
    orders = Order.objects.select_related('warehouse', 'assigned_to')
    
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    if warehouse_filter != 'all':
        orders = orders.filter(warehouse_id=warehouse_filter)
    
    if date_filter == 'today':
        orders = orders.filter(created_date=date.today())
    elif date_filter == 'yesterday':
        yesterday = date.today() - timedelta(days=1)
        orders = orders.filter(created_date=yesterday)
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=7)
        orders = orders.filter(created_date__gte=week_start)
    
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_address__icontains=search_query)
        )
    
    page = request.GET.get('page', 1)
    paginator = Paginator(orders.order_by('-created_date'), 50)
    
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)
    
    warehouses = Warehouse.objects.all()
    
    context = {
        'page_title': 'Orders Management',
        'orders': orders_page,
        'warehouses': warehouses,
        'status_filter': status_filter,
        'warehouse_filter': warehouse_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'status_choices': Order.ORDER_STATUS,
    }
    
    return render(request, 'orders.html', context)


@login_required
def agents_view(request):
    status_filter = request.GET.get('status', 'all')
    warehouse_filter = request.GET.get('warehouse', 'all')
    
    agents = Agent.objects.select_related('warehouse')
    
    if status_filter == 'active':
        agents = agents.filter(is_active=True, checkin_time__isnull=False)
    elif status_filter == 'inactive':
        agents = agents.filter(is_active=False)
    elif status_filter == 'not_checked_in':
        agents = agents.filter(is_active=True, checkin_time__isnull=True)
    
    if warehouse_filter != 'all':
        agents = agents.filter(warehouse_id=warehouse_filter)
    
    search_query = request.GET.get('search', '')
    if search_query:
        agents = agents.filter(
            Q(name__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    today = date.today()
    
    # Calculate checked_in_agents count
    checked_in_agents = Agent.objects.filter(
        is_active=True,
        checkin_time__isnull=False
    ).count()
    
    for agent in agents:
        try:
            metrics = AgentDailyMetrics.objects.get(agent=agent, date=today)
            agent.today_orders = metrics.total_orders
            agent.today_earnings = metrics.total_earnings
            agent.today_distance = metrics.total_distance
        except AgentDailyMetrics.DoesNotExist:
            agent.today_orders = 0
            agent.today_earnings = 0
            agent.today_distance = 0
    
    page = request.GET.get('page', 1)
    paginator = Paginator(agents.order_by('name'), 50)
    
    try:
        agents_page = paginator.page(page)
    except PageNotAnInteger:
        agents_page = paginator.page(1)
    except EmptyPage:
        agents_page = paginator.page(paginator.num_pages)
    
    warehouses = Warehouse.objects.all()
    
    context = {
        'page_title': 'Agents Management',
        'agents': agents_page,
        'warehouses': warehouses,
        'status_filter': status_filter,
        'warehouse_filter': warehouse_filter,
        'search_query': search_query,
        'today': today,
        'checked_in_agents': checked_in_agents,  # ADD THIS LINE
    }
    
    return render(request, 'agents.html', context)


@login_required
def warehouses_view(request):
    warehouses = Warehouse.objects.annotate(
        agent_count=Count('agents', filter=Q(agents__is_active=True)),
        order_count=Count('orders', filter=Q(orders__created_date=date.today())),
        pending_orders=Count('orders', filter=Q(orders__status='pending') & Q(orders__created_date=date.today())),
        assigned_orders=Count('orders', filter=Q(orders__status='assigned') & Q(orders__created_date=date.today()))
    )
    
    context = {
        'page_title': 'Warehouses',
        'warehouses': warehouses,
        'today': date.today(),
    }
    
    return render(request, 'warehouses.html', context)


@login_required
def allocation_view(request):
    from allocation.allocation_logic import DeliveryAllocationSystem
    
    today = date.today()
    warehouses = Warehouse.objects.all()
    
    warehouse_status = []
    for warehouse in warehouses:
        pending_orders = Order.objects.filter(
            warehouse=warehouse,
            status='pending',
            created_date__lte=today
        ).count()
        
        assigned_today = Order.objects.filter(
            warehouse=warehouse,
            status='assigned',
            delivery_date=today
        ).count()
        
        checked_in_agents = Agent.objects.filter(
            warehouse=warehouse,
            is_active=True,
            checkin_time__isnull=False
        ).count()
        
        warehouse_status.append({
            'warehouse': warehouse,
            'pending_orders': pending_orders,
            'assigned_today': assigned_today,
            'checked_in_agents': checked_in_agents,
            'can_allocate': pending_orders > 0 and checked_in_agents > 0,
        })
    
    recent_allocations = AssignmentLog.objects.select_related(
        'agent', 'order', 'agent__warehouse'
    ).order_by('-assigned_at')[:20]
    
    context = {
        'page_title': 'Order Allocation',
        'warehouse_status': warehouse_status,
        'recent_allocations': recent_allocations,
        'today': today,
        'allocator': DeliveryAllocationSystem(),
    }
    
    return render(request, 'allocation.html', context)


@login_required
def reports_view(request):
    """OPTIMIZED Reports dashboard"""
    start_date_str = request.GET.get(
        'start_date',
        (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')  # Reduced to 30 days
    )
    end_date_str = request.GET.get(
        'end_date',
        date.today().strftime('%Y-%m-%d')
    )

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = date.today() - timedelta(days=30)  # Reduced
        end_date = date.today()

    # -------------------------
    # SIMPLE DAILY COUNTS (LIMITED TO 30 DAYS)
    # -------------------------
    daily_summaries = []
    current_date = start_date
    days_count = 0
    
    while current_date <= end_date and days_count < 30:  # Max 30 days
        total = Order.objects.filter(created_date=current_date).count()
        delivered = Order.objects.filter(
            status='delivered', 
            created_date=current_date
        ).count()
        
        daily_summaries.append({
            'report_date': current_date,
            'total_orders': total,
            'delivered_orders': delivered,
            'deferred_orders': 0,  # Simplified
            'total_earnings': 0,    # Simplified
        })
        
        current_date += timedelta(days=1)
        days_count += 1

    # -------------------------
    # SIMPLE WAREHOUSE STATS
    # -------------------------
    warehouse_stats = Warehouse.objects.all()[:10]  # Limit to 10 warehouses
    
    simple_stats = []
    for warehouse in warehouse_stats:
        total = Order.objects.filter(
            warehouse=warehouse,
            created_date__range=[start_date, end_date]
        ).count()
        
        delivered = Order.objects.filter(
            warehouse=warehouse,
            status='delivered',
            created_date__range=[start_date, end_date]
        ).count()
        
        simple_stats.append({
            'name': warehouse.name,
            'total_orders': total,
            'delivered_orders': delivered,
            'delivery_rate': round((delivered / total * 100), 2) if total > 0 else 0,
        })

    # -------------------------
    # SIMPLE TOP AGENTS (LIMIT TO 20)
    # -------------------------
    top_agents = []
    agents = Agent.objects.filter(is_active=True)[:20]  # Limit to 20 agents
    
    for agent in agents:
        delivered = Order.objects.filter(
            assigned_to=agent,
            status='delivered',
            created_date__range=[start_date, end_date]
        ).count()
        
        if delivered > 0:  # Only include agents with deliveries
            top_agents.append({
                'agent__name': agent.name,
                'agent__employee_id': agent.employee_id,
                'agent__warehouse__name': agent.warehouse.name,
                'total_orders': delivered,
                'total_earnings': delivered * 20,  # Simplified calculation
            })
    
    # Sort and limit to top 10
    top_agents = sorted(top_agents, key=lambda x: x['total_orders'], reverse=True)[:10]

    # -------------------------
    # SIMPLE CHART DATA
    # -------------------------
    dates = [s['report_date'].strftime('%Y-%m-%d') for s in daily_summaries]
    orders_data = [s['total_orders'] for s in daily_summaries]

    context = {
        'page_title': 'Reports & Analytics',
        'daily_summaries': daily_summaries[:15],  # Limit display to 15 days
        'warehouse_stats': simple_stats,
        'top_agents': top_agents,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'dates_json': json.dumps(dates),
        'orders_data_json': json.dumps(orders_data),
        'earnings_data_json': json.dumps([0] * len(dates)),  # Placeholder
        'deferred_data_json': json.dumps([0] * len(dates)),  # Placeholder
    }

    return render(request, 'reports.html', context)


@login_required
def automation_view(request):
    import redis
    
    services = {
        'redis': False,
        'celery_worker': False,
        'celery_beat': False,
        'django': True,
    }
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        services['redis'] = True
    except:
        services['redis'] = False
    
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'celery' in cmdline:
                if 'worker' in cmdline:
                    services['celery_worker'] = True
                elif 'beat' in cmdline:
                    services['celery_beat'] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    from delivery_system.celery import app
    scheduled_tasks = []
    for task_name, task_schedule in app.conf.beat_schedule.items():
        if 'schedule' in task_schedule:
            schedule = task_schedule['schedule']
            if hasattr(schedule, 'is_due'):
                next_run = schedule.is_due(datetime.now())
                scheduled_tasks.append({
                    'name': task_name,
                    'task': task_schedule['task'],
                    'next_run': next_run.next_run if hasattr(next_run, 'next_run') else 'Unknown',
                    'enabled': True
                })
    
    from django_celery_results.models import TaskResult
    recent_tasks = TaskResult.objects.order_by('-date_created')[:10]
    
    context = {
        'page_title': 'Automation Control',
        'services': services,
        'scheduled_tasks': scheduled_tasks,
        'recent_tasks': recent_tasks,
        'all_running': all(services.values()),
    }
    
    return render(request, 'automation.html', context)


@login_required
def start_allocation(request):
    from allocation.tasks import run_daily_allocation
    
    if request.method == 'POST':
        warehouse_id = request.POST.get('warehouse_id')
        
        if warehouse_id == 'all':
            result = run_daily_allocation.delay()
            message = f"Allocation started for all warehouses. Task ID: {result.id}"
        else:
            from allocation.allocation_logic import DeliveryAllocationSystem
            allocator = DeliveryAllocationSystem()
            try:
                result = allocator.allocate_orders_to_agents(int(warehouse_id))
                message = f"Allocation completed for warehouse {warehouse_id}. Assigned: {result['assigned_orders']}, Deferred: {result['deferred_orders']}"
            except Exception as e:
                message = f"Error: {str(e)}"
        
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def start_service(request):
    import subprocess
    
    if request.method == 'POST':
        service = request.POST.get('service')
        
        try:
            if service == 'redis':
                subprocess.run(['brew', 'services', 'start', 'redis'], check=True)
            elif service == 'celery_worker':
                import os
                from django.conf import settings
                cmd = f"cd {settings.BASE_DIR} && source venv/bin/activate && celery -A delivery_system worker --loglevel=info --detach"
                subprocess.run(cmd, shell=True, check=True)
            elif service == 'celery_beat':
                import os
                from django.conf import settings
                cmd = f"cd {settings.BASE_DIR} && source venv/bin/activate && celery -A delivery_system beat --loglevel=info --detach"
                subprocess.run(cmd, shell=True, check=True)
            
            return JsonResponse({'success': True, 'message': f'{service} started successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def stop_service(request):
    import subprocess
    import psutil
    
    if request.method == 'POST':
        service = request.POST.get('service')
        
        try:
            if service == 'redis':
                subprocess.run(['brew', 'services', 'stop', 'redis'], check=True)
            elif service in ['celery_worker', 'celery_beat']:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'celery' in cmdline:
                            if service == 'celery_worker' and 'worker' in cmdline:
                                psutil.Process(proc.info['pid']).terminate()
                            elif service == 'celery_beat' and 'beat' in cmdline:
                                psutil.Process(proc.info['pid']).terminate()
                    except:
                        pass
            
            return JsonResponse({'success': True, 'message': f'{service} stopped successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def agent_detail(request, agent_id):
    try:
        agent = Agent.objects.select_related('warehouse').get(id=agent_id)
        
        seven_days_ago = date.today() - timedelta(days=7)
        daily_metrics = AgentDailyMetrics.objects.filter(
            agent=agent,
            date__gte=seven_days_ago
        ).order_by('date')
        
        recent_assignments = AssignmentLog.objects.filter(
            agent=agent
        ).select_related('order').order_by('-assignment_date')[:20]
        
        total_orders = sum(m.total_orders for m in daily_metrics)
        total_earnings = sum(float(m.total_earnings) for m in daily_metrics)
        total_distance = sum(float(m.total_distance) for m in daily_metrics)
        
        avg_daily_orders = total_orders / len(daily_metrics) if daily_metrics else 0
        if avg_daily_orders >= 50:
            performance_tier = 'High (₹42/order)'
        elif avg_daily_orders >= 25:
            performance_tier = 'Medium (₹35/order)'
        else:
            performance_tier = 'Base (₹500 min)'
        
        context = {
            'page_title': f'Agent: {agent.name}',
            'agent': agent,
            'daily_metrics': daily_metrics,
            'recent_assignments': recent_assignments,
            'total_orders': total_orders,
            'total_earnings': total_earnings,
            'total_distance': total_distance,
            'avg_daily_orders': round(avg_daily_orders, 2),
            'performance_tier': performance_tier,
        }
        
        return render(request, 'agent_detail.html', context)
        
    except Agent.DoesNotExist:
        return redirect('agents')


@login_required
def order_detail(request, order_id):
    try:
        order = Order.objects.select_related(
            'warehouse', 'assigned_to'
        ).get(id=order_id)
        
        assignment_log = AssignmentLog.objects.filter(order=order).first()
        
        from allocation.allocation_logic import DeliveryAllocationSystem
        allocator = DeliveryAllocationSystem()
        
        distance = allocator.calculate_distance(
            order.warehouse.latitude, order.warehouse.longitude,
            order.customer_latitude, order.customer_longitude
        )
        
        estimated_time = distance * 5
        
        context = {
            'page_title': f'Order: {order.order_id}',
            'order': order,
            'assignment_log': assignment_log,
            'distance': round(distance, 2),
            'estimated_time': round(estimated_time, 2),
        }
        
        return render(request, 'order_detail.html', context)
        
    except Order.DoesNotExist:
        return redirect('orders')
    
@login_required
def create_delivery_attempt(request, order_id):
    """Create a delivery attempt (for agents)"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        agent = get_object_or_404(Agent, user=request.user)
        
        # Get previous attempt number
        previous_attempts = DeliveryAttempt.objects.filter(order=order).count()
        attempt_number = previous_attempts + 1
        
        # Get form data
        status = request.POST.get('status', 'failed')
        notes = request.POST.get('notes', '')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Create delivery attempt
        attempt = DeliveryAttempt.objects.create(
            order=order,
            agent=agent,
            attempt_number=attempt_number,
            status=status,
            notes=notes,
            latitude=latitude,
            longitude=longitude
        )
        
        # Update order status based on attempt
        if status == 'successful':
            order.status = 'delivered'
            order.delivery_date = timezone.now().date()
        elif status == 'failed' and attempt_number >= 3:
            order.status = 'deferred'
        elif status == 'rescheduled':
            # Keep as assigned for next attempt
            pass
        
        order.save()
        
        return redirect('order_detail', order_id=order.id)
    
    return redirect('dashboard')

@login_required
def delivery_attempt_list(request, order_id):
    """List all delivery attempts for an order"""
    order = get_object_or_404(Order, id=order_id)
    attempts = DeliveryAttempt.objects.filter(order=order).order_by('-attempted_at')
    
    context = {
        'order': order,
        'attempts': attempts,
    }
    return render(request, 'delivery/delivery_attempts.html', context)

@csrf_exempt
def api_create_delivery_attempt(request):
    """API endpoint for mobile app to create delivery attempt"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            order = get_object_or_404(Order, order_id=data.get('order_id'))
            agent = get_object_or_404(Agent, user=request.user)
            
            # Get previous attempt number
            previous_attempts = DeliveryAttempt.objects.filter(order=order).count()
            
            attempt = DeliveryAttempt.objects.create(
                order=order,
                agent=agent,
                attempt_number=previous_attempts + 1,
                status=data.get('status', 'failed'),
                notes=data.get('notes', ''),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                photo_url=data.get('photo_url', ''),
                signature_url=data.get('signature_url', '')
            )
            
            # Update order status
            if attempt.status == 'successful':
                order.status = 'delivered'
                order.delivery_date = timezone.now().date()
                order.save()
            
            return JsonResponse({
                'success': True,
                'attempt_id': attempt.id,
                'attempt_number': attempt.attempt_number
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})
    

class CustomLoginView(LoginView):
    """Custom login view that redirects to admin login"""
    template_name = 'admin/login.html'  # Use admin login template
    
    def dispatch(self, request, *args, **kwargs):
        # If already authenticated, redirect to dashboard
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('dashboard')