from django import template
import json

register = template.Library()

@register.filter
def json_pretty(value):
    """Format JSON data nicely for display"""
    try:
        return json.dumps(value, indent=2)
    except (TypeError, ValueError):
        return str(value)
