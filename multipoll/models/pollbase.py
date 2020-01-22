from __future__ import annotations  # noqa: T484

import json
import logging
import math
from collections import defaultdict
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, TypeVar, Union
from typing import TYPE_CHECKING
from typing import cast

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.base import ModelBase
from django.http import Http404
from django.shortcuts import get_object_or_404

from typedmodels.models import TypedModel

from typing_extensions import Protocol

from multipoll import slack
from multipoll.models.fields import TimestampField
from multipoll.models.user import User
from multipoll.utils import absolute_url_without_request

if TYPE_CHECKING:
    import multipoll.electoralsystems


Vote = Tuple[User, Optional[int]]
Poll = TypeVar('Poll', bound='PollBase')
FullVote = TypeVar('FullVote', bound='FullVoteBase')
PartialVote = TypeVar('PartialVote', bound='PartialVoteBase')

logger = logging.getLogger(__name__)


class ModelState(Protocol):
    adding: bool
    db: str


class PollBase(TypedModel):
    class Meta:
        get_latest_by = "timestamp"
        ordering = ("timestamp",)
        indexes = (models.Index(fields=('timestamp',)),)

    MAX_OPTIONS: ClassVar[int] = 99

    _state: ModelState
    timestamp = TimestampField(primary_key=True)
    channel: models.CharField[str, str] = models.CharField(max_length=9, null=False)
    question: models.CharField[str, str] = models.CharField(max_length=200, null=False)
    options: ArrayField[List[str], List[str]] = ArrayField(models.CharField(max_length=100,
                                                                            null=False,
                                                                            blank=False),
                                                           null=False, blank=False,
                                                           size=MAX_OPTIONS)

    supported_systems = ("approval",)
    default_system = "approval"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.timestamp:
            self.post_poll()

        super(PollBase, self).save(*args, **kwargs)

        self.update_poll()

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

    def post_poll(self) -> None:
        newline = '\n'
        text = f"*{self.question}*\n\n{newline.join(self.get_formatted_votes())}"
        attachments = self.format_attachments()
        ts = slack.post_message(self.channel, text, attachments)
        self.timestamp = ts

    def update_poll(self) -> None:
        newline = '\n'
        text = f"*{self.question}*\n{self.get_absolute_url()}\n" \
               + f"{newline.join(self.get_formatted_votes())}"
        attachments = self.format_attachments()
        slack.update_message(self.channel, self.timestamp_str, text, attachments)

    def get_formatted_votes(self, system: Optional[str] = None) -> List[str]:
        return [f"({'' if s is None else s}) {o} "  # noqa: IF100
                + f"({', '.join([f'{u.name}[{w}]' for u, w in votes if w is not None])})"
                for o, votes, s in self.get_all_votes_with_option_and_score(system)]

    def visualized_results(self, system: Optional[str] = None) -> Optional[Union[bytes, str]]:
        return self.visualize_options(self.question, self.options, self.all_votes, system)

    def get_all_votes_with_option_and_score(self, system: Optional[str] = None) \
            -> List[Tuple[str, List[Vote], float]]:
        return self.order_options(self.options, self.all_votes, system)

    @property
    def formatted_votes(self) -> List[str]:
        return self.get_formatted_votes()

    @property
    def timestamp_str(self) -> Optional[str]:
        if self.timestamp:
            return TimestampField.normalize_to_timestamp(self.timestamp)
        else:
            return None

    @property
    def all_votes(self) -> Dict[User, FullVote]:
        votes = self.full_votes
        partial_votes = self.partial_votes
        for user, vote in partial_votes.items():
            if user in votes:
                for i, weight in enumerate(vote.weights):
                    if weight is not None:
                        votes[user].weights[i] = weight
            else:
                votes[user] = vote
        return votes

    @property
    def all_votes_with_option_and_score(self) -> List[Tuple[str, List[Vote], float]]:
        return self.get_all_votes_with_option_and_score()

    @property
    def partial_votes(self) -> Dict[User, FullVote]:
        FullVoteType = getattr(self, "FullVoteType")  # noqa: N806
        votes: Dict[User, FullVote] = defaultdict(FullVoteType)
        PartialVoteType = getattr(self, "PartialVoteType")  # noqa: N806
        partial_vote_set = PartialVoteType.name.lower() + "_set"
        for vote in getattr(self, partial_vote_set).all():
            if vote.weight is not None:
                votes[vote.user].weights[vote.option] = vote.weight
                votes[vote.user].user = vote.user
                votes[vote.user].poll = self
        return votes

    @property
    def full_votes(self) -> Dict[User, FullVote]:
        FullVoteType = getattr(self, "FullVoteType")  # noqa: N806
        votes: Dict[User, FullVote] = defaultdict(FullVoteType)
        full_vote_set = FullVoteType.name.lower() + "_set"
        vote: FullVote
        for vote in getattr(self, full_vote_set).all():
            votes[vote.user] = vote
        return votes

    @classmethod
    def get_electoral_system(cls: Type[Poll], system: Optional[str] = None) \
            -> Type[multipoll.electoralsystems.electoral_system]:
        from multipoll.electoralsystems import get_electoral_system
        if system is None:
            system = cls.default_system
        elif system not in cls.supported_systems:
            raise Http404("System is not supported")
        return get_electoral_system(system)

    @classmethod
    def order_options(cls: Type[Poll], options: List[str],
                      votes: Dict[User, FullVote], system: Optional[str] = None) \
            -> List[Tuple[str, List[Vote], float]]:
        system_cls = cls.get_electoral_system(system)
        return system_cls.order_options(options, list(votes.values()))

    @classmethod
    def visualize_options(cls: Type[Poll], question: str, options: List[str],
                          votes: Dict[User, FullVote], system: Optional[str] = None) \
            -> Optional[Union[bytes, str]]:
        system_cls = cls.get_electoral_system(system)
        return system_cls.visualize_results(question, options, list(votes.values()))

    @classmethod
    def add(cls: Type[Poll], channel: str, question: str, options: List[str]) -> Poll:
        return cls.objects.create(channel=channel, question=question, options=options)

    @classmethod
    def timestamped(cls: Type[Poll], timestamp: str) -> Poll:
        return get_object_or_404(cls, timestamp=timestamp)


def default_options_inner() -> List[Optional[int]]:
    return [None for _ in range(PollBase.MAX_OPTIONS)]


class FullVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...],  # noqa: N804
                attrs: Dict[str, Any]) -> Type[FullVoteBase]:
        attrs['name'] = name
        parents = [b for b in bases if isinstance(b, FullVoteMeta)]  # noqa: T499
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
    class Meta:
        abstract = True
        ordering = ('poll', 'user')
        indexes = (models.Index(fields=('poll',)),)

    _state: ModelState
    poll_model: Type[PollBase]
    poll: PollBase
    weights: List
    user_secret: models.CharField[str, str] = models.CharField(max_length=11, null=True)
    user: models.ForeignKey[User, User] = models.ForeignKey(User, on_delete=models.CASCADE,
                                                            null=False)

    def save(self, *args: Any, **kwargs: Any) -> None:
        super(FullVoteBase, self).save(*args, **kwargs)
        self.poll.update_poll()

    def get_form(self) -> forms.ModelForm:
        ...

    @property
    def options(self) -> List[Tuple[str, Optional[int]]]:
        poll: PollBase = self.poll
        return list(zip(poll.options, self.weights))

    @classmethod
    def find_and_validate_if_exists(cls, poll: PollBase, user: User,
                                    user_secret: str) -> Optional[FullVoteBase]:
        filtered = cls.objects.filter(poll=poll, user=user)
        if filtered:
            if filtered[0].user_secret == user_secret:
                return filtered[0]
            else:
                raise PermissionDenied()
        else:
            return None

    @classmethod
    def find_and_validate_or_create_verified(cls: Type[FullVote], poll: Poll, user: User,
                                             user_secret: str) -> FullVote:
        existing = cls.find_and_validate_if_exists(poll, user, user_secret)
        if existing:
            return existing  # noqa: T484
        else:
            vote = cls(poll=poll, user=user, user_secret=user_secret)
            vote.save()
            return vote


class PartialVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...],  # noqa: N804
                attrs: Dict[str, Any]) -> Type[PartialVote]:
        attrs['name'] = name
        parents = [b for b in bases if isinstance(b, PartialVoteMeta)]  # noqa: T484
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
    class Meta:
        abstract = True

    _state: ModelState
    poll_model: Type[PollBase]
    poll: PollBase

    option: models.PositiveSmallIntegerField[int, int] = \
        models.PositiveSmallIntegerField(null=False)
    user: models.ForeignKey[User, User] = models.ForeignKey(User, on_delete=models.CASCADE,
                                                            null=False)

    def save(self, *args: Any, **kwargs: Any) -> None:
        super(PartialVoteBase, self).save(*args, **kwargs)
        self.poll.update_poll()

    @property
    def chosen_option(self) -> str:
        return self.poll.options[self.option]

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
