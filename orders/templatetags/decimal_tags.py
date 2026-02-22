from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def add_decimal(value, arg):
    """
    Add two decimal values together.
    Usage: {{ value|add_decimal:arg }}
    """
    try:
        value = Decimal(str(value)) if value else Decimal('0')
        arg = Decimal(str(arg)) if arg else Decimal('0')
        return value + arg
    except (ValueError, TypeError):
        return value


@register.filter
def subtract_decimal(value, arg):
    """
    Subtract arg from value.
    Usage: {{ value|subtract_decimal:arg }}
    """
    try:
        value = Decimal(str(value)) if value else Decimal('0')
        arg = Decimal(str(arg)) if arg else Decimal('0')
        return value - arg
    except (ValueError, TypeError):
        return value


@register.filter
def multiply_decimal(value, arg):
    """
    Multiply two decimal values.
    Usage: {{ value|multiply_decimal:arg }}
    """
    try:
        value = Decimal(str(value)) if value else Decimal('0')
        arg = Decimal(str(arg)) if arg else Decimal('1')
        return value * arg
    except (ValueError, TypeError):
        return value


@register.filter
def apply_discount(value, discount_percent):
    """
    Apply discount percentage to a value.
    Usage: {{ price|apply_discount:discount_percent }}
    Returns value rounded to 2 decimal places.
    """
    try:
        value = Decimal(str(value)) if value else Decimal('0')
        discount_percent = Decimal(str(discount_percent)) if discount_percent else Decimal('0')
        result = value * (1 - discount_percent / 100)
        return result.quantize(Decimal('0.01'))
    except (ValueError, TypeError):
        return value
