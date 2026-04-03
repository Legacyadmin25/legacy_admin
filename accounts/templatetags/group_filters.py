from django import template

register = template.Library()

@register.filter
def group_name(groups, name):
    """Returns True if the user is in the group with the given name."""
    return groups.filter(name=name).exists()
