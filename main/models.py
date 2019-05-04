import random
import string
from typing import Dict, List

from django.db import models


class Teams(models.Model):
    access_token = models.CharField(max_length=1000)
    team_name = models.CharField(max_length=1000)
    team_id = models.CharField(primary_key=True, max_length=1000)
    incoming_webhook_url = models.CharField(max_length=1000)
    incoming_webhook_configuration_url = models.CharField(max_length=1000)
    last_changed = models.DateTimeField(auto_now=True, auto_now_add=False)
    created = models.DateTimeField(auto_now=False, auto_now_add=True, editable=False)


class Polls(models.Model):
    timestamp = models.CharField(max_length=100, primary_key=True, unique=True)
    channel = models.CharField(max_length=1000)
    question = models.CharField(max_length=1000)
    options = models.CharField(max_length=1000)


class Votes(models.Model):
    vote_id = models.AutoField(primary_key=True)
    poll = models.ForeignKey(Polls, on_delete=models.CASCADE)
    option = models.CharField(max_length=100)
    users = models.CharField(max_length=1000)


class DistributedPoll(models.Model):
    name = models.CharField(max_length=50, unique=True)


class Block(models.Model):
    name = models.CharField(max_length=100)
    poll = models.ForeignKey(DistributedPoll, on_delete=models.CASCADE)


class Question(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    question = models.CharField(max_length=1000)
    options = models.CharField(max_length=1000)
    id = models.CharField(max_length=8, default=None, blank=True, primary_key=True)  # noqa: A003

    # Code courtesy of https://stackoverflow.com/a/37359808
    # Sample of an ID generator - could be any string/number generator
    # For a 6-char field, this one yields 2.1 billion unique IDs
    @staticmethod
    def id_generator(size: int = 8, chars: str = string.ascii_lowercase) -> str:
        return ''.join(random.choice(chars) for _ in range(size))

    def save(self: "Question", *args: List, **kwargs: Dict) -> None:
        if not self.id:
            # Generate ID once, then check the db. If exists, keep trying.
            self.id = self.id_generator()
            while Question.objects.filter(id=self.id).exists():
                self.id = self.id_generator()
        super(Question, self).save(*args, **kwargs)


class User(models.Model):
    name = models.CharField(max_length=100)
    id = models.CharField(max_length=50, primary_key=True)  # noqa: A003


class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
