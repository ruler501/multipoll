from __future__ import annotations  # noqa: T484

from functools import total_ordering
from typing import Dict, Union

from django.db import models
from django.http import Http404


@total_ordering
class User(models.Model):
    class Meta:
        get_latest_by = "name"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'])
        ]

    name: models.CharField[str, str] = models.CharField(max_length=30, null=False, primary_key=True)

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, User):
            return self.name == other.name
        else:
            return False

    def __lt__(self, other: object) -> bool:
        if isinstance(other, User):
            return self.name < other.name
        else:
            return False

    @staticmethod
    def find_or_create(user: Union[Dict, str]) -> User:
        if isinstance(user, dict):
            user_name = user['name']
        elif isinstance(user, str):
            user_name = user
        else:
            raise Http404()
        return User.objects.get_or_create(name=user_name)[0]
