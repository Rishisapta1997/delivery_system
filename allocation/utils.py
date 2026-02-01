# allocation/utils.py
from datetime import datetime, date
from decimal import Decimal
from delivery.models import Order, AgentDailyMetrics


def get_daily_summary(report_date: date = None):
    """Get daily summary report"""
    if report_date is None:
        report_date = date.today()
    
    metrics = AgentDailyMetrics.objects.filter(date=report_date, is_active=True)
    
    total_agents = metrics.count()
    total_orders = sum(m.total_orders for m in metrics)
    total_distance = sum(float(m.total_distance) for m in metrics)
    total_earnings = sum(float(m.total_earnings) for m in metrics)
    
    # Get deferred orders
    deferred_orders = Order.objects.filter(status='deferred', created_date=report_date).count()
    
    # Calculate average metrics
    avg_orders = total_orders / total_agents if total_agents > 0 else 0
    avg_distance = total_distance / total_agents if total_agents > 0 else 0
    avg_earnings = total_earnings / total_agents if total_agents > 0 else 0
    
    # Performance tiers
    high_performers = metrics.filter(total_orders__gte=50).count()
    medium_performers = metrics.filter(total_orders__gte=25, total_orders__lt=50).count()
    low_performers = metrics.filter(total_orders__lt=25).count()
    
    return {
        'report_date': report_date,
        'total_agents': total_agents,
        'total_orders': total_orders,
        'total_distance_km': round(total_distance, 2),
        'total_earnings': round(total_earnings, 2),
        'deferred_orders': deferred_orders,
        'avg_orders_per_agent': round(avg_orders, 2),
        'avg_distance_per_agent': round(avg_distance, 2),
        'avg_earnings_per_agent': round(avg_earnings, 2),
        'high_performers': high_performers,
        'medium_performers': medium_performers,
        'low_performers': low_performers,
        'cost_per_order': round(total_earnings / total_orders, 2) if total_orders > 0 else 0,
    }


def calculate_agent_performance(agent_id: int, start_date: date, end_date: date):
    """Calculate performance metrics for an agent over a date range"""
    metrics = AgentDailyMetrics.objects.filter(
        agent_id=agent_id,
        date__gte=start_date,
        date__lte=end_date,
        is_active=True
    ).order_by('date')
    
    total_days = metrics.count()
    total_orders = sum(m.total_orders for m in metrics)
    total_earnings = sum(float(m.total_earnings) for m in metrics)
    total_distance = sum(float(m.total_distance) for m in metrics)
    
    return {
        'agent_id': agent_id,
        'period': f"{start_date} to {end_date}",
        'total_days_worked': total_days,
        'total_orders_delivered': total_orders,
        'total_earnings': round(total_earnings, 2),
        'total_distance_km': round(total_distance, 2),
        'avg_orders_per_day': round(total_orders / total_days, 2) if total_days > 0 else 0,
        'avg_earnings_per_day': round(total_earnings / total_days, 2) if total_days > 0 else 0,
        'performance_tier': 'High' if (total_orders / total_days) >= 50 else 
                          'Medium' if (total_orders / total_days) >= 25 else 'Low'
    }