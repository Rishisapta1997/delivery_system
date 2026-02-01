from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from datetime import date

from .models import Order, Agent


@login_required
@require_POST
@csrf_exempt
def assign_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        if order.status != 'pending':
            return JsonResponse({
                'success': False,
                'message': f'Order is already {order.status}'
            })
        
        from allocation.allocation_logic import DeliveryAllocationSystem
        allocator = DeliveryAllocationSystem()
        agents = allocator.get_available_agents(order.warehouse.id, date.today())
        
        if not agents:
            return JsonResponse({
                'success': False,
                'message': 'No available agents found'
            })
        
        order.assigned_to = agents[0]
        order.status = 'assigned'
        order.delivery_date = date.today()
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order assigned to {agents[0].name}'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Order not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def update_order_status(request, order_id):
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if not new_status:
            return JsonResponse({
                'success': False,
                'message': 'Status is required'
            })
        
        order = Order.objects.get(id=order_id)
        old_status = order.status
        order.status = new_status
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order status changed from {old_status} to {new_status}'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Order not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def checkin_agent(request, agent_id):
    try:
        agent = Agent.objects.get(id=agent_id)
        
        if not agent.is_active:
            return JsonResponse({
                'success': False,
                'message': 'Agent is inactive'
            })
        
        from datetime import datetime
        agent.checkin_time = datetime.now().time()
        agent.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Agent checked in successfully'
        })
        
    except Agent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Agent not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })