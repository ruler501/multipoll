import copy
import datetime
import logging
import random
import string
from typing import Dict, List, Union, Any, Optional, Callable

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models

from django import forms


class TimestampField(models.CharField):
    def __init__(self, **kwargs: Optional[Any]):
        kwargs['max_length'] = 50
        super(TimestampField, self).__init__(**kwargs)

    def db_type(self, connection):
        return 'TIMESTAMP'

    @staticmethod
    def to_python_static(value: Union[str, datetime.datetime, float]) -> str:
        logging.info(f'to_python: {value}, {type(value)}')

        if isinstance(value, str):
            try:
                float(value)
                return value
            except ValueError:
                # TODO: Investigate type checker saying fromisoformat doesn't exist.
                return str(datetime.datetime.fromisoformat(value).replace(tzinfo=datetime.timezone.utc).timestamp())
        elif isinstance(value, datetime.datetime):
            return str(value.replace(tzinfo=datetime.timezone.utc).timestamp())
        elif isinstance(value, float):
            return str(value)

        raise TypeError("value was not a recognized type")

    def to_python(self, value):
        return TimestampField.to_python_static(value)

    @staticmethod
    def from_db_value_static(value) -> datetime.datetime:
        logging.info(f'db_value: {value}, {type(value)}')
        if isinstance(value, str):
            try:
                fvalue = float(value)
                return datetime.datetime.utcfromtimestamp(fvalue)
            except ValueError:
                # TODO: Investigate type checker saying fromisoformat doesn't exist.
                return datetime.datetime.fromisoformat(value).replace(tzinfo=datetime.timezone.utc)
        elif isinstance(value, datetime.datetime):
            # TODO: Figure out why type checker says we're missing positional arguments for replace
            return value.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(value, float):
            # TODO: Figure out why type checker says we're missing positional arguments for replace
            return datetime.datetime.replace(tzinfo=datetime.timezone.utc)

        raise TypeError("value was not a recognized type")

    def from_db_value(self, value, expression, connection, context):
        return TimestampField.from_db_value_static(value)

    @staticmethod
    def get_prep_value_static(value: Union[str, datetime.datetime, float]) -> str:
        logging.info(f'get_prep_value: {value} {type(value)}')

        if isinstance(value, datetime.datetime):
            dt = value
        else:
            try:
                dt = datetime.datetime.utcfromtimestamp(float(value))
            except ValueError:
                return value
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_prep_value(self, value: Union[str, datetime.datetime, float]) -> str:
        return TimestampField.get_prep_value_static(value)

class User(models.Model):
    name = models.CharField(max_length=100, null=False, unique=True)

    class Meta:
        get_latest_by = "name"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'])
        ]


class Poll(models.Model):
    MAX_OPTIONS = 99
    timestamp: datetime.datetime = TimestampField(primary_key=True)
    channel: str = models.CharField(max_length=9, null=False)
    question: str = models.CharField(max_length=200, null=False)
    options: List[str] = ArrayField(models.CharField(max_length=100, null=False), null=False, size=MAX_OPTIONS)

    @property
    def timestamp_str(self):
        result = str(self.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp())
        print(f'timestamp_str: {result}')
        return result

    @property
    def votes(self) -> List[List[str]]:
        partial = self.partial_votes
        complete = self.complete_votes
        votes = [a + b for a, b in zip(partial, complete)]
        votes = [sorted(option) for option in votes]
        return votes

    @property
    def formatted_votes(self) -> List[str]:
        votes = sorted(enumerate(self.votes), key=lambda vs: len(vs[1]), reverse=True)
        return [f"({len(vs)}) {self.options[i]} ({', '.join(vs)})" for i, vs in votes]


    @property
    def partial_votes(self) -> List[List[str]]:
        votes: List[List[str]] = [[] for _ in self.options]
        for vote in self.vote_set.all():
            votes[vote.option].append(vote.user.name)

        votes = [sorted(option) for option in votes]
        return votes

    @property
    def complete_votes(self) -> List[List[str]]:
        votes: List[List[str]] = [[] for _ in self.options]
        for vote in self.completevote_set.all():
            for option in vote.options:
                ind = self.options.index(option)
                votes[ind].append(vote.user.name)
        votes = [sorted(option) for option in votes]
        return votes

    class Meta:
        get_latest_by = "timestamp"
        ordering = ["timestamp"]
        unique_together = [["timestamp"]]
        indexes = [models.Index(fields=['timestamp'])]

    def get_absolute_url(self):
        return f"/polls/{self.timestamp}/"


def default_options_inner():
    return [False]*Poll.MAX_OPTIONS


class CompleteVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, null=False)
    options_inner = ArrayField(models.BooleanField(null=False), size=Poll.MAX_OPTIONS,
                               default=default_options_inner)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    user_secret = models.CharField(max_length=11, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['poll', 'user'], name='SingleVoteCopy')
        ]
        ordering = ['poll', 'user']
        indexes = [models.Index(fields=['poll'])]

    @property
    def options(self) -> List[str]:
        values = self.poll.options
        return [values[i] for i, toggle in enumerate(self.options_inner[:len(values)]) if toggle]

    @options.setter
    def options(self, value: List[str]) -> None:
        print(value, len(value))
        values = self.poll.options
        our_value = [(val in value) for val in values]
        if sum([int(x) for x in our_value]) != len(value):
            print(our_value)
            print(values)
            print(value)
            raise ValidationError("Included duplicate or invalid values")
        our_value += [False] * (99 - len(our_value))
        self.options_inner = our_value


def validate_vote(poll: Poll, user: User, user_secret: str):
    filtered = CompleteVote.objects.filter(poll=poll, user=user)
    if filtered:
        if filtered[0].user_secret == user_secret:
            return filtered[0]
        else:
            raise PermissionDenied()
    return None


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, null=False)
    option = models.IntegerField(null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    @property
    def chosen_option(self) -> str:
        return self.poll.options[self.option]

    class Meta:
        unique_together = [['poll', 'option', 'user']]
        ordering = ['poll', 'option']


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
    options = ArrayField(models.CharField(max_length=50), null=False, size=99)
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
