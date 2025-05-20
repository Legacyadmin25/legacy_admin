from django import template

register = template.Library()

@register.filter
def split(value, delimiter=","):
    """
    Split a string by the given delimiter.
    Usage in template: {{ "a,b,c"|split:"," }}  → ["a", "b", "c"]
    """
    try:
        return value.split(delimiter)
    except Exception:
        return []

@register.filter
def to_int(value):
    """
    Convert the value to int, or return 0 on failure.
    Usage: {{ "123"|to_int }} → 123
           {{ "foo"|to_int }} → 0
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@register.filter(name="custom_range")
def custom_range(start, end):
    """
    Return a range from start to end.
    Usage: {% for i in 1|custom_range:5 %}{{ i }}{% endfor %}
    """
    try:
        return range(int(start), int(end))
    except (ValueError, TypeError):
        return []

@register.filter
def get_item(form, name):
    """
    Given a Django Form (or dict-like) and a field/key name, return form[name].
    Usage in template: {% with form|get_item:"field_name" as field %}…{% endwith %}
    """
    try:
        return form[name]
    except Exception:
        return None
