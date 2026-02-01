# allocation/tasks.py
from celery import shared_task
from datetime import datetime
from allocation.allocation_logic import DeliveryAllocationSystem
from delivery.models import Warehouse
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_daily_allocation():
    """Celery task to run daily allocation at 7:00 AM"""
    logger.info(f"Starting daily allocation at {datetime.now()}")
    
    allocation_system = DeliveryAllocationSystem()
    results = []
    
    # Get all warehouses
    warehouses = Warehouse.objects.all()
    
    for warehouse in warehouses:
        try:
            result = allocation_system.allocate_orders_to_agents(warehouse.id)
            results.append(result)
            logger.info(f"Warehouse {warehouse.name}: {result}")
        except Exception as e:
            logger.error(f"Error allocating orders for warehouse {warehouse.name}: {str(e)}")
    
    # Log summary
    total_assigned = sum(r['assigned_orders'] for r in results)
    total_deferred = sum(r['deferred_orders'] for r in results)
    total_cost = sum(r['total_cost'] for r in results)
    
    logger.info(f"""
    ========== ALLOCATION SUMMARY ==========
    Total Warehouses: {len(warehouses)}
    Total Orders Assigned: {total_assigned}
    Total Orders Deferred: {total_deferred}
    Total Daily Cost: ₹{total_cost:.2f}
    =======================================
    """)
    
    return results