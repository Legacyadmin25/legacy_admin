import logging
from django import template
from django.contrib.auth.models import Group

register = template.Library()

# Set up logging to see when the filter is applied
logger = logging.getLogger(__name__)

@register.filter(name='has_group')
def has_group(user, group_name):
    """Check if user belongs to a specific group"""
    if not user or not user.is_authenticated:
        logger.debug(f"User is not authenticated or invalid: {user}")
        return False
    if not hasattr(user, 'groups'):
        logger.debug(f"User does not have 'groups' attribute: {user}")
        return False
    logger.debug(f"Checking if {user} is in group: {group_name}")
    return user.groups.filter(name=group_name).exists()
