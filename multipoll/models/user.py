from __future__ import annotations  # noqa: T484

from functools import total_ordering
from typing import Dict, Union

from django.db import models
from django.http import Http404


@total_ordering
class User(models.Model):
    name: models.CharField[str, str] = models.CharField(max_length=30, null=False, primary_key=True)

    class Meta:
        get_latest_by = "name"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'])
        ]

    @staticmethod
    def find_or_create(user: Union[Dict, str]) -> User:
        if isinstance(user, dict):
            user_name = user['name']
        elif isinstance(user, str):
            user_name = user
        else:
            raise Http404()
        return User.objects.get_or_create(name=user_name)[0]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return False
        else:
            return self.name == other.name

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, User):
            return False
        else:
            return self.name < other.name

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)