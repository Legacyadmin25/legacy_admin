from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_names):
    """
    Usage: {% if user|has_group:"Group1,Group2" %}
    Returns True if the user is in ANY of the given groups (comma-separated).
    Handles spaces between names.
    """
    if not user or not hasattr(user, 'groups'):
        return False
    if not group_names:
        return False
    group_list = [g.strip() for g in group_names.split(',') if g.strip()]
    return user.groups.filter(name__in=group_list).exists()
