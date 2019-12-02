from django import template

from multipoll.electoralsystems import get_electoral_system

register = template.Library()


@register.filter(name='system_name')
def system_name(value: str) -> str:
    return get_electoral_system(value).label