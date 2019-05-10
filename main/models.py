import datetime
import logging
import random
import string
from typing import Dict, List

from django.contrib.postgres.fields import ArrayField
from django.db import models


class TimestampField(models.CharField):
    def __init__(self, **kwargs):
        kwargs['max_length'] = 50
        super(TimestampField, self).__init__(**kwargs)

    def db_type(self, connection):
        return 'TIMESTAMP'

    def to_python(self, value: float) -> str:
        logging.info(f'to_python: {value}')
        return str(value)

    def get_prep_value(self, value: str) -> str:
        logging.info(f'get_prep_value: {value}')
        return str(value)


class User(models.Model):
    name = models.CharField(max_length=100, null=False, unique=True)

    class Meta:
        get_latest_by = "name"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'])
        ]


class Poll(models.Model):
    timestamp = TimestampField(primary_key=True)
    channel = models.CharField(max_length=9, null=False)
    question = models.CharField(max_length=200, null=False)
    options = ArrayField(models.CharField(max_length=50), null=False, max_length=99)

    @property
    def votes(self) -> List[List[str]]:
        votes: List[List[str]] = [[] for _ in self.options]
        for vote in self.vote_set.all():
            votes[vote.option].append(vote.user.name)
        return votes

    class Meta:
        get_latest_by = "timestamp"
        ordering = ["timestamp"]


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, null=False)
    option = models.IntegerField(null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    @property
    def chosen_option(self) -> str:
        return self.poll.options[self.option]

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['poll', 'option', 'user'], name='Single Vote Copy')
        ]
        ordering = ['option']


class DistributedPoll(models.Model):
    name = models.CharField(max_length=50, unique=True, null=False)


class Block(models.Model):
    name = models.CharField(max_length=100, null=False)
    poll = models.ForeignKey(DistributedPoll, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['poll'])
        ]


class Question(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE, null=False)
    question = models.CharField(max_length=200, null=False)
    options = ArrayField(models.CharField(max_length=50), null=False, max_length=100)
    id = models.CharField(max_length=4, default=None, blank=True, primary_key=True)  # noqa: A003

    # Code courtesy of https://stackoverflow.com/a/37359808
    # Sample of an ID generator - could be any string/number generator
    # For a 6-char field, this one yields 2.1 billion unique IDs
    @staticmethod
    def id_generator(size: int = 4, chars: str = string.ascii_lowercase) -> str:
        return ''.join(random.choice(chars) for _ in range(size))

    def save(self: "Question", *args: List, **kwargs: Dict) -> None:
        if not self.id:
            # Generate ID once, then check the db. If exists, keep trying.
            self.id = self.id_generator()
            while Question.objects.filter(id=self.id).exists():
                self.id = self.id_generator()
        super(Question, self).save(*args, **kwargs)

    @property
    def responses(self) -> List[List[str]]:
        votes: List[List[str]] = [[] for _ in self.options]
        for response in self.response_set.all():
            votes[response.option].append(response.user.name)
        return votes

    class Meta:
        indexes = [
            models.Index(fields=["block"])
        ]


class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=False)
    option = models.IntegerField(null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    @property
    def chosen_option(self) -> str:
        return self.question.options[self.option]

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['question', 'option', 'user'], name='Single Response Copy')
        ]
        indexes = [
            models.Index(fields=["question"])
        ]
