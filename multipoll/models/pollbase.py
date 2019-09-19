import datetime
import json
import math

from typing import List, Tuple, TypeVar, Type, Optional, Dict

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import QuerySet, Manager
from django.db.models.base import ModelBase
from django.shortcuts import get_object_or_404
from typedmodels.models import TypedModel

from multipoll import slack
from multipoll.electoralsystems import get_electoral_system
from multipoll.models.fields import TimestampField
from multipoll.models.user import User
from multipoll.utils import Numeric, absolute_url_without_request, OptNumeric

Vote = Tuple[User, OptNumeric]
VForm = TypeVar('VForm', bound=forms.ModelForm)
ModelField = TypeVar('ModelField', bound=models.Field)


class PollBase(TypedModel):
    fullvote_set: QuerySet
    partialvote_set: QuerySet
    FullVoteType: Type['FullVote']
    PartialVoteType: Type['PartialVote']

    MAX_OPTIONS = 99

    timestamp: datetime.datetime = TimestampField(primary_key=True)
    channel: str = models.CharField(max_length=9, null=False)
    question: str = models.CharField(max_length=200, null=False)
    options: List[str] = ArrayField(models.CharField(max_length=100, null=False), null=False, size=MAX_OPTIONS)

    class Meta:
        get_latest_by = "timestamp"
        ordering = ("timestamp",)
        indexes = (models.Index(fields=('timestamp',)),)

    class PollMeta:
        weight_field: ModelField

    supported_systems = ("approval",)
    default_system = "approval"

    @property
    def timestamp_str(self):
        result = TimestampField.to_python_static(self.timestamp)
        return result

    @property
    def all_votes(self) -> List[List[Vote]]:
        if self.timestamp:
            partial = self.partial_votes
            complete = self.full_votes
            all_votes = [a + b for a, b in zip(partial, complete)]
            return [sorted(votes) for votes in all_votes]
        else:
            return [[] for _ in self.options]

    @property
    def formatted_votes(self) -> List[str]:
        options_with_votes = self.order_options(self.options, self.all_votes)
        votes = list(zip(*options_with_votes))[1]
        # noinspection PyTypeChecker
        return [f"({self.calculate_weight(i, votes)}) {ovs[0]} ({', '.join([f'{u}[{w}]' for u, w in ovs[1]])})"
                for i, ovs in enumerate(options_with_votes)]

    @property
    def partial_votes(self) -> List[List[Vote]]:
        votes: List[List[Vote]] = [[] for _ in self.options]
        vote: PartialVote
        for vote in getattr(self, getattr(self, "PartialVoteType").name.lower() + "_set").all():
            if vote.weight != 0:
                votes[vote.option].append((vote.user, vote.weight))
        votes = [sorted(option, key=lambda v: v[0].name) for option in votes]
        return votes

    @property
    def full_votes(self) -> List[List[Vote]]:
        votes: List[List[Vote]] = [[] for _ in self.options]
        vote: FullVote
        for vote in getattr(self, getattr(self, "FullVoteType").name.lower() + "_set").all():
            for option, weight in vote.options:
                ind = self.options.index(option)
                votes[ind].append((vote.user, weight))
        votes = [sorted(option, key=lambda v: v[0].name) for option in votes]
        return votes

    @classmethod
    def order_options(cls: Type['Poll'], options: List[str], votes: List[List[Vote]]) -> List[Tuple[str, List[Vote]]]:
        system = get_electoral_system(cls.default_system)
        return system.order_options(options, votes)

    @classmethod
    def calculate_weight(cls: Type['Poll'], ind: int, votes: List[List[Vote]]) -> Numeric:
        system = get_electoral_system(cls.default_system)
        return system.calculate_weight(ind, votes)

    def get_absolute_url(self) -> Optional[str]:
        if self.timestamp:
            return absolute_url_without_request(f"/polls/{self.timestamp_str}/")
        else:
            return None

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]: ...

    def format_attachments(self, include_add_more: bool = True) -> str:
        actions = [self.create_attachment_for_option(i) for i in range(len(self.options))]

        if include_add_more:
            actions.append({"name": "addMore", "text": "Add More", "type": "button", "value": "Add More"})
        attachments = []
        for i in range(int(math.ceil(len(actions) / 5.0))):
            attachment = {"text": "", "callback_id": "options",
                          "attachment_type": "default", "actions": actions[5 * i: 5 * i + 5]}
            attachments.append(attachment)

        return json.dumps(attachments)

    @classmethod
    def add(cls: Type['Poll'], channel: str, question: str, options: List[str]) -> 'Poll':
        return cls.objects.create(channel=channel, question=question, options=options)

    @classmethod
    def timestamped(cls: Type['Poll'], timestamp: str) -> 'Poll':
        return get_object_or_404(cls, timestamp=timestamp)

    def post_poll(self) -> str:
        newline = '\n'
        text = f"*{self.question}*\n\n{newline.join(self.formatted_votes)}"
        attachments = self.format_attachments()
        return slack.post_message(self.channel, text, attachments)

    def update_poll(self) -> None:
        newline = '\n'
        text = f"*{self.question}*\n{self.get_absolute_url()}\n{newline.join(self.formatted_votes)}"
        attachments = self.format_attachments()
        timestamp = self.timestamp_str
        slack.update_message(self.channel, timestamp, text, attachments)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.timestamp:
            ts = self.post_poll()
            self.timestamp = TimestampField.from_db_value_static(ts)

        super().save(force_insert, force_update, using, update_fields)

        self.update_poll()


Poll = TypeVar('Poll', bound=PollBase)


def default_options_inner() -> List[OptNumeric]:
    return [None for _ in range(PollBase.MAX_OPTIONS)]


class FullVoteMetaClass(ModelBase):
    def __new__(mcs, name, bases, attrs):
        attrs['name'] = name
        parents = [b for b in bases if isinstance(b, FullVoteMetaClass)]
        if parents:
            _meta = attrs['Meta']
            poll_model = attrs["poll_model"]
            if 'poll' not in attrs:
                attrs['poll'] = models.ForeignKey(poll_model, on_delete=models.CASCADE, null=False,
                                                  related_name=f"{name.lower()}_set")
            if 'weights' not in attrs:
                attrs['weights'] = ArrayField(getattr(getattr(poll_model, "PollMeta"), "weight_field"),
                                              size=PollBase.MAX_OPTIONS, default=default_options_inner)
            setattr(_meta, "constraints", (models.UniqueConstraint(fields=('poll', 'user'),
                                                                   name=f'Single{name}Copy'),))

            assert 'get_form' in attrs

        bases = bases + (models.Model,)

        newtype = super().__new__(mcs, name, bases, attrs)
        if parents:
            poll_model = getattr(newtype, "poll_model")
            setattr(poll_model, "FullVoteType", newtype)
        return newtype


class FullVoteBase(metaclass=FullVoteMetaClass):
    objects: Manager
    poll: Poll
    weights: List[OptNumeric]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    user_secret = models.CharField(max_length=11, null=True)

    class Meta:
        abstract = True
        ordering = ('poll', 'user')
        indexes = (models.Index(fields=('poll',)),)

    @property
    def options(self) -> List[Tuple[str, OptNumeric]]:
        poll: PollBase = self.poll
        return list(zip(poll.options, self.weights))

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None) -> None:
        # noinspection PyUnresolvedReferences
        super().save(force_insert, force_update, using, update_fields)
        self.poll.update_poll()

    def get_form(self) -> VForm: ...

    @classmethod
    def validate_and_find_existing(cls: Type['FullVote'], poll: Poll, user: User, user_secret: str) \
            -> Optional['FullVote']:
        filtered = cls.objects.filter(poll=poll, user=user)
        if filtered:
            if filtered[0].user_secret == user_secret:
                return filtered[0]
            else:
                raise PermissionDenied()
        return None

    @classmethod
    def find_or_create_verified(cls: Type['FullVote'], poll: Poll, user_name: str, user_secret: str) -> 'FullVote':
        user = User.find_or_create(user_name)
        existing = cls.validate_and_find_existing(poll, user, user_secret)
        if existing:
            return existing
        else:
            vote = cls(poll=poll, user=user, user_secret=user_secret)
            vote.save()
            return vote


FullVote = TypeVar('FullVote', bound=FullVoteBase)


class PartialVoteMetaClass(ModelBase):
    def __new__(mcs, name, bases, attrs):
        attrs['name'] = name
        parents = [b for b in bases if isinstance(b, PartialVoteMetaClass)]
        if parents:
            _meta = attrs['Meta']
            poll_model = attrs["poll_model"]
            if 'poll' not in attrs:
                attrs['poll'] = models.ForeignKey(poll_model, on_delete=models.CASCADE, null=False,
                                                  related_name=f"{name.lower()}_set")
            if 'weight' not in attrs:
                attrs['weight'] = getattr(getattr(poll_model, "PollMeta"), "weight_field")
            setattr(_meta, "constraints", (models.UniqueConstraint(fields=('poll', 'option', 'user',),
                                                                   name=f'Single{name}Copy'),))
            setattr(_meta, "indexes", (models.Index(fields=('poll',)),))
            setattr(_meta, "ordering", ('poll', 'option', 'user'))
            assert 'weight' in attrs
            assert 'get_form' in attrs

        bases = bases + (models.Model,)

        newtype = super().__new__(mcs, name, bases, attrs)
        if parents:
            poll_model = getattr(newtype, "poll_model")
            setattr(poll_model, "PartialVoteType", newtype)
        return newtype


class PartialVoteBase(metaclass=PartialVoteMetaClass):
    poll: Poll
    objects: Manager
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    option = models.PositiveSmallIntegerField()
    weight: Numeric

    class Meta:
        abstract = True

    @property
    def chosen_option(self) -> str:
        return self.poll.options[self.option]

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None) -> None:
        # noinspection PyUnresolvedReferences
        super().save(force_insert, force_update, using, update_fields)
        self.poll.update_poll()

    def get_form(self) -> VForm: ...

    @classmethod
    def add(cls: Type['PartialVote'], poll: Poll, user: User, option: int, weight: Numeric) -> 'PartialVote':
        partial_vote = cls.objects.get_or_create(poll=poll, user=user, option=option)[0]
        partial_vote.weight = weight
        partial_vote.save()
        return partial_vote


PartialVote = TypeVar('PartialVote', bound=PartialVoteBase)