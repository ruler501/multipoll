from typing import Union, Dict

from django.db import models
from django.http import Http404


class User(models.Model):
    name = models.CharField(max_length=30, null=False, unique=True)

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