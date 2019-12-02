from typing import List

from django import template

from multipoll.electoralsystems import get_electoral_system
from multipoll.models import PollBase

register = template.Library()


@register.filter(name='system_name')
def system_name(value: str) -> str:
    return get_electoral_system(value).label


@register.filter(name='formatted_results')
def formatted_results(value: PollBase, arg: str) -> List[str]:
    return value.get_formatted_votes(arg)