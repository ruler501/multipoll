from __future__ import annotations  # noqa: T484

import json
import logging
import math
from collections import defaultdict
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, TypeVar
from typing import cast

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.base import ModelBase
from django.shortcuts import get_object_or_404

from typedmodels.models import TypedModel

from multipoll import slack
from multipoll.models.fields import TimestampField
from multipoll.models.user import User
from multipoll.utils import absolute_url_without_request

Numeric = TypeVar('Numeric')
Vote = Tuple[User, Optional[Numeric]]
Poll = TypeVar('Poll', bound='PollBase')
FullVote = TypeVar('FullVote', bound='FullVoteBase')
PartialVote = TypeVar('PartialVote', bound='PartialVoteBase')

logger = logging.getLogger(__name__)


class PollBase(TypedModel):
    MAX_OPTIONS: ClassVar[int] = 99

    timestamp = TimestampField(primary_key=True)
    channel: models.CharField[str, str] = models.CharField(max_length=9, null=False)
    question: models.CharField[str, str] = models.CharField(max_length=200, null=False)
    options: ArrayField[List[str], List[str]] = ArrayField(models.CharField(max_length=100,
                                                                            null=False,
                                                                            blank=False),
                                                           null=False, blank=False,
                                                           size=MAX_OPTIONS)

    class Meta:
        get_latest_by = "timestamp"
        ordering = ("timestamp",)
        indexes = (models.Index(fields=('timestamp',)),)

    supported_systems = ("approval",)
    default_system = "approval"

    @property
    def timestamp_str(self) -> Optional[str]:
        if self.timestamp:
            return TimestampField.normalize_to_timestamp(self.timestamp)
        else:
            return None

    @property
    def all_votes(self) -> Dict[User, FullVote]:
        votes = self.full_votes
        votes.update(self.partial_votes)
        return votes

    @property
    def all_votes_with_option_and_score(self) -> List[Tuple[str, List[Vote], float]]:
        return self.order_options(self.options, self.all_votes)

    @property
    def formatted_votes(self) -> List[str]:
        return [f"({'' if s is None else s}) {o} "
                + f"({', '.join([f'{u.name}[{w}]' for u, w in votes if w is not None])})"
                for o, votes, s in self.all_votes_with_option_and_score]

    @property
    def partial_votes(self) -> Dict[User, FullVote]:
        # noinspection PyPep8Naming
        FullVoteType = getattr(self, "FullVoteType")
        votes: Dict[User, FullVote] = defaultdict(FullVoteType)
        # noinspection PyPep8Naming
        PartialVoteType = getattr(self, "PartialVoteType")
        partial_vote_set = PartialVoteType.name.lower() + "_set"
        for vote in getattr(self, partial_vote_set).all():
            if vote.weight is not None and vote.weight not in (False, "off", "False", "false", "f"):
                votes[vote.user].weights[vote.option] = vote.weight
        return votes

    @property
    def full_votes(self) -> Dict[User, FullVote]:
        # noinspection PyPep8Naming
        FullVoteType = getattr(self, "FullVoteType")
        votes: Dict[User, FullVote] = defaultdict(FullVoteType)
        full_vote_set = FullVoteType.name.lower() + "_set"
        vote: FullVote
        for vote in getattr(self, full_vote_set).all():
            votes[vote.user] = vote
        return votes

    @classmethod
    def order_options(cls: Type[Poll], options: List[str],
                      votes: Dict[User, FullVote]) -> List[Tuple[str, List[Vote], float]]:
        from multipoll.electoralsystems import get_electoral_system
        system = get_electoral_system(cls.default_system)
        return system.order_options(options, list(votes.values()))

    def get_absolute_url(self) -> Optional[str]:
        if self.timestamp:
            return absolute_url_without_request(f"/polls/{self.timestamp_str}/")
        else:
            return None

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        ...

    def format_attachments(self, include_add_more: bool = True) -> str:
        actions = [self.create_attachment_for_option(i) for i in range(len(self.options))]

        if include_add_more:
            actions.append({"name": "addMore", "text": "Add More", "type": "button",
                            "value": "Add More"})
        attachments = []
        for i in range(int(math.ceil(len(actions) / 5.0))):
            attachment = {"text": "", "callback_id": "options",
                          "attachment_type": "default", "actions": actions[5 * i: 5 * i + 5]}
            attachments.append(attachment)

        return json.dumps(attachments)

    @classmethod
    def add(cls: Type[Poll], channel: str, question: str, options: List[str]) -> Poll:
        return cls.objects.create(channel=channel, question=question, options=options)

    @classmethod
    def timestamped(cls: Type[Poll], timestamp: str) -> Poll:
        return get_object_or_404(cls, timestamp=timestamp)

    def post_poll(self) -> None:
        newline = '\n'
        text = f"*{self.question}*\n\n{newline.join(self.formatted_votes)}"
        attachments = self.format_attachments()
        ts = slack.post_message(self.channel, text, attachments)
        self.timestamp = ts

    def update_poll(self) -> None:
        newline = '\n'
        text = f"*{self.question}*\n{self.get_absolute_url()}\n{newline.join(self.formatted_votes)}"
        attachments = self.format_attachments()
        slack.update_message(self.channel, self.timestamp_str, text, attachments)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.timestamp:
            self.post_poll()

        super(PollBase, self).save(*args, **kwargs)

        self.update_poll()


def default_options_inner() -> List[Optional[Numeric]]:
    return [None for _ in range(PollBase.MAX_OPTIONS)]


class FullVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...],
                attrs: Dict[str, Any]) -> Type[FullVoteBase]:
        attrs['name'] = name
        parents = [b for b in bases if isinstance(b, FullVoteMeta)]
        if parents:
            _meta = attrs['Meta']
            poll_model = attrs["poll_model"]
            attrs['poll'] = models.ForeignKey(poll_model, on_delete=models.CASCADE, null=False,
                                              related_name=f"{name.lower()}_set")
            weight_args = getattr(poll_model, "weight_field_args")
            attrs['weights'] = ArrayField(getattr(poll_model,
                                                  "WeightFieldType")(**weight_args),
                                          size=PollBase.MAX_OPTIONS, default=default_options_inner)
            setattr(_meta, "constraints", (models.UniqueConstraint(fields=('poll', 'user'),
                                                                   name=f'Single{name}Copy'),))

            assert 'get_form' in attrs

        new_type = cast(Type['FullVoteBase'], super().__new__(mcs, name, bases, attrs))
        if parents:
            poll_model = getattr(new_type, "poll_model")
            setattr(poll_model, "FullVoteType", new_type)
        return new_type


class FullVoteBase(models.Model, metaclass=FullVoteMeta):
    poll_model: Type[PollBase]
    poll: PollBase
    user: models.ForeignKey[User, User] = models.ForeignKey(User, on_delete=models.CASCADE,
                                                            null=False)
    user_secret: models.CharField[str, str] = models.CharField(max_length=11, null=True)
    weights: List

    class Meta:
        abstract = True
        ordering = ('poll', 'user')
        indexes = (models.Index(fields=('poll',)),)

    @property
    def options(self) -> List[Tuple[str, Optional[Numeric]]]:
        poll: PollBase = self.poll
        return list(zip(poll.options, self.weights))

    def save(self, *args: Any, **kwargs: Any) -> None:
        # noinspection PyUnresolvedReferences
        super(FullVoteBase, self).save(*args, **kwargs)
        self.poll.update_poll()

    def get_form(self) -> forms.ModelForm:
        ...

    @classmethod
    def find_and_validate_if_exists(cls, poll: PollBase, user: User,
                                    user_secret: str) -> Optional[FullVote]:
        filtered = cls.objects.filter(poll=poll, user=user)
        if filtered:
            if filtered[0].user_secret == user_secret:
                return filtered[0]
            else:
                raise PermissionDenied()
        return None

    @classmethod
    def find_and_validate_or_create_verified(cls: Type[FullVote], poll: Poll, user_name: str,
                                             user_secret: str) -> FullVote:
        user = User.find_or_create(user_name)
        existing = cls.find_and_validate_if_exists(poll, user, user_secret)
        if existing:
            return existing
        else:
            vote = cls(poll=poll, user=user, user_secret=user_secret)
            vote.save()
            return vote


class PartialVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any])\
            -> Type[PartialVote]:
        attrs['name'] = name
        parents = [b for b in bases if isinstance(b, PartialVoteMeta)]
        poll_model: Type[PollBase]
        if parents:
            _meta = attrs['Meta']
            poll_model = attrs["poll_model"]
            set_name = f"{name.lower()}_set"
            attrs['poll'] = models.ForeignKey(poll_model, on_delete=models.CASCADE, null=False,
                                              related_name=set_name)
            weight_args = getattr(poll_model, "weight_field_args")
            attrs['weight'] = getattr(poll_model, "WeightFieldType")(**weight_args)
            setattr(_meta, "constraints", (models.UniqueConstraint(fields=('poll', 'option',
                                                                           'user',),
                                                                   name=f'Single{name}Copy'),))
            setattr(_meta, "indexes", (models.Index(fields=('poll',)),))
            setattr(_meta, "ordering", ('poll', 'option', 'user'))

        new_type = cast(Type[PartialVote], super().__new__(mcs, name, bases, attrs))
        if parents:
            poll_model = new_type.poll_model
            setattr(poll_model, "PartialVoteType", new_type)
        return new_type


class PartialVoteBase(models.Model, metaclass=PartialVoteMeta):
    poll_model: Type[PollBase]
    poll: PollBase

    user: models.ForeignKey[User, User] = models.ForeignKey(User, on_delete=models.CASCADE,
                                                            null=False)
    option: models.PositiveSmallIntegerField[int, int] = \
        models.PositiveSmallIntegerField(null=False)

    class Meta:
        abstract = True

    @property
    def chosen_option(self) -> str:
        return self.poll.options[self.option]

    def save(self, *args: Any, **kwargs: Any) -> None:
        super(PartialVoteBase, self).save(*args, **kwargs)
        self.poll.update_poll()

    @classmethod
    def find_or_create(cls: Type[PartialVote], poll: PollBase, user: User,
                       option: int) -> PartialVote:
        partial_votes = cls.objects.filter(poll=poll, user=user, option=option)
        if partial_votes:
            partial_vote = partial_votes[0]
        else:
            # metaclass shenanigans prevent proper type checking the kwargs
            partial_vote = cls(poll=poll, user=user, option=option)  # noqa: T484
        return partial_vote