from django import template

register = template.Library()

@register.filter
def sum_attr(items, attr):
    try:
        return sum(getattr(item, attr, 0) for item in items)
    except:
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def filter_by(items, filter_string):
    if not items:
        return []
    
    try:
        attr, value = filter_string.split(':')
        return [item for item in items if getattr(item, attr, None) == value]
    except:
        return []