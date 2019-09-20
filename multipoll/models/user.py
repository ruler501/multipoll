from functools import total_ordering
from typing import Union, Dict

from django.db import models
from django.http import Http404

@total_ordering
class User(models.Model):
    name = models.CharField(max_length=30, null=False, primary_key=True)

    class Meta:
        get_latest_by = "name"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'])
        ]

    @staticmethod
    def find_or_create(user: Union[Dict, str]) -> 'User':
        if isinstance(user, dict):
            user_name = user['name']
        elif isinstance(user, str):
            user_name = user
        else:
            raise Http404()
        return User.objects.get_or_create(name=user_name)[0]

    def __eq__(self, other: 'User') -> bool:
        return self.name == getattr(other, "name", None)

    def __lt__(self, other: 'User') -> bool:
        return self.name < getattr(other, "name", "")

    def __str__(self) -> str:
        return self.name 
