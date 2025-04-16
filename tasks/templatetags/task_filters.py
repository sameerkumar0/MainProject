from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """
    Split a string by the given delimiter and return a list.
    Usage: {{ value|split:"delimiter" }}
    """
    return value.split(arg)

@register.filter
def format_status(value):
    """
    Format a status string by replacing underscores with spaces and capitalizing each word.
    Usage: {{ value|format_status }}
    """
    return value.replace('_', ' ').title()
