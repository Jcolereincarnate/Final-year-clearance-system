"""
Custom template filters for clearance app
"""
from django import template

register = template.Library()


@register.filter
def dict_lookup(dictionary, key):
    """
    Lookup a value in a dictionary by key
    Usage: {{ my_dict|dict_lookup:my_key }}
    """
    if dictionary and key:
        return dictionary.get(key)
    return None