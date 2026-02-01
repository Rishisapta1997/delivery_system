# allocation/allocation_logic.py
import math
from datetime import datetime, date
from typing import List, Dict, Tuple
from decimal import Decimal
from django.db import transaction
from delivery.models import Agent, Order, Warehouse, AgentDailyMetrics, AssignmentLog


class DeliveryAllocationSystem:
    def __init__(self):
        self.MAX_WORKING_HOURS = 10
        self.MAX_DISTANCE_KM = 100
        self.KM_TO_MINUTES = 5  # 1 km = 5 minutes
        
    def calculate_distance(self, lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_available_agents(self, warehouse_id: int, current_date: date) -> List[Agent]:
        """Get all agents who have checked in today"""
        return list(Agent.objects.filter(
            warehouse_id=warehouse_id,
            is_active=True,
            checkin_time__isnull=False
        ))
    
    def get_pending_orders(self, warehouse_id: int) -> List[Order]:
        """Get all pending orders for a warehouse"""
        return list(Order.objects.filter(
            warehouse_id=warehouse_id,
            status='pending'
        ).order_by('created_date', 'priority'))
    
    def can_assign_order(self, agent_metrics: AgentDailyMetrics, 
                        distance_to_order: float, 
                        current_orders: int) -> Tuple[bool, str]:
        """Check if order can be assigned to agent based on constraints"""
        
        # Check distance constraint
        new_total_distance = agent_metrics.total_distance + distance_to_order
        if new_total_distance > self.MAX_DISTANCE_KM:
            return False, "Distance limit exceeded"
        
        # Check time constraint (1 km = 5 minutes)
        additional_time = distance_to_order * self.KM_TO_MINUTES / 60  # Convert to hours
        new_total_hours = agent_metrics.total_working_hours + additional_time
        if new_total_hours > self.MAX_WORKING_HOURS:
            return False, "Working hours limit exceeded"
        
        return True, ""
    
    def calculate_order_priority(self, order: Order, warehouse: Warehouse) -> float:
        """Calculate priority score for an order"""
        distance = self.calculate_distance(
            warehouse.latitude, warehouse.longitude,
            order.customer_latitude, order.customer_longitude
        )
        
        # Lower distance = higher priority
        # Higher order priority value = higher priority
        priority_score = (1 / (distance + 0.1)) * order.priority
        
        return priority_score
    
    def allocate_orders_to_agents(self, warehouse_id: int):
        """Main allocation algorithm"""
        today = date.today()
        warehouse = Warehouse.objects.get(id=warehouse_id)
        
        agents = self.get_available_agents(warehouse_id, today)
        pending_orders = self.get_pending_orders(warehouse_id)
        
        # Initialize or get daily metrics for agents
        agent_metrics_map = {}
        for agent in agents:
            metrics, created = AgentDailyMetrics.objects.get_or_create(
                agent=agent,
                date=today,
                defaults={
                    'total_orders': 0,
                    'total_distance': 0,
                    'total_working_hours': 0,
                    'is_active': True
                }
            )
            agent_metrics_map[agent.id] = metrics
        
        assigned_orders = []
        deferred_orders = []
        
        # Sort orders by priority score
        orders_with_priority = []
        for order in pending_orders:
            priority_score = self.calculate_order_priority(order, warehouse)
            orders_with_priority.append((priority_score, order))
        
        orders_with_priority.sort(reverse=True, key=lambda x: x[0])
        
        # Allocation algorithm
        for priority_score, order in orders_with_priority:
            best_agent = None
            best_distance = float('inf')
            
            # Calculate distance from warehouse to order
            order_distance = self.calculate_distance(
                warehouse.latitude, warehouse.longitude,
                order.customer_latitude, order.customer_longitude
            )
            
            # Find suitable agent
            for agent in agents:
                metrics = agent_metrics_map[agent.id]
                
                can_assign, reason = self.can_assign_order(
                    metrics, order_distance, metrics.total_orders
                )
                
                if can_assign:
                    # Prefer agent with fewer orders to balance load
                    if metrics.total_orders < 30:  # Try to keep agents under 30 orders initially
                        best_agent = agent
                        best_distance = order_distance
                        break
                    elif order_distance < best_distance:
                        best_agent = agent
                        best_distance = order_distance
            
            if best_agent:
                # Assign order to agent
                with transaction.atomic():
                    order.assigned_to = best_agent
                    order.status = 'assigned'
                    order.delivery_date = today
                    order.save()
                    
                    # Update agent metrics
                    metrics = agent_metrics_map[best_agent.id]
                    metrics.total_orders += 1
                    metrics.total_distance += Decimal(str(order_distance))
                    metrics.total_working_hours += Decimal(str(order_distance * self.KM_TO_MINUTES / 60))
                    metrics.save()
                    
                    # Create assignment log
                    AssignmentLog.objects.create(
                        agent=best_agent,
                        order=order,
                        assignment_date=today,
                        distance_from_warehouse=Decimal(str(order_distance)),
                        estimated_delivery_time=int(order_distance * self.KM_TO_MINUTES)
                    )
                    
                    assigned_orders.append(order)
            else:
                # No suitable agent found, defer order
                order.status = 'deferred'
                order.save()
                deferred_orders.append(order)
        
        return {
            'warehouse': warehouse.name,
            'total_agents': len(agents),
            'total_pending_orders': len(pending_orders),
            'assigned_orders': len(assigned_orders),
            'deferred_orders': len(deferred_orders),
            'agents_utilization': self.calculate_agent_utilization(agent_metrics_map),
            'total_cost': self.calculate_total_cost(agent_metrics_map),
        }
    
    def calculate_agent_utilization(self, agent_metrics_map: Dict) -> Dict:
        """Calculate utilization metrics for agents"""
        total_orders = 0
        high_performers = 0
        medium_performers = 0
        low_performers = 0
        
        for metrics in agent_metrics_map.values():
            total_orders += metrics.total_orders
            if metrics.total_orders >= 50:
                high_performers += 1
            elif metrics.total_orders >= 25:
                medium_performers += 1
            else:
                low_performers += 1
        
        return {
            'total_orders': total_orders,
            'high_performers': high_performers,
            'medium_performers': medium_performers,
            'low_performers': low_performers,
            'avg_orders_per_agent': total_orders / len(agent_metrics_map) if agent_metrics_map else 0,
        }
    
    def calculate_total_cost(self, agent_metrics_map: Dict) -> Decimal:
        """Calculate total cost for the day"""
        total_cost = Decimal('0.00')
        
        for metrics in agent_metrics_map.values():
            total_cost += metrics.total_earnings
        
        return total_cost