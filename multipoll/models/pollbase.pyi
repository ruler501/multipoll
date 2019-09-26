import logging
from typing import Any, ClassVar, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.base import ModelBase

from typedmodels.models import TypedModel

from typing_extensions import Protocol

from multipoll.electoralsystems import electoral_system
from multipoll.models.fields import TimestampField
from multipoll.models.user import User

_Numeric = TypeVar('_Numeric')
Vote = Tuple[User, Optional[_Numeric]]
_Poll = TypeVar('_Poll', bound='PollBase')
_FullVote = TypeVar('_FullVote', bound='FullVoteBase')
_PartialVote = TypeVar('_PartialVote', bound='PartialVoteBase')

logger = logging.getLogger(__name__)


class ModelState(Protocol):
    adding: bool
    db: str


class PollBase(TypedModel, Generic[_Numeric]):
    class Meta:
        get_latest_by: str
        ordering: Tuple[str, ...]
        indexes: Tuple[models.Index, ...]

    MAX_OPTIONS: ClassVar[int]

    _state: ModelState
    FullVoteType: Type[FullVoteBase[_Numeric]]
    PartialVoteType: Type[PartialVoteBase[_Numeric]]
    timestamp: TimestampField
    channel: models.CharField[str, str]
    question: models.CharField[str, str]
    options: ArrayField[List[str], List[str]]
    supported_systems: Tuple[str, ...]
    default_system: str

    def save(self, *args: Any, **kwargs: Any) -> None:
        ...

    def get_absolute_url(self) -> Optional[str]:
        ...

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        ...

    def format_attachments(self, include_add_more: bool) -> str:
        ...

    def post_poll(self) -> None:
        ...

    def update_poll(self) -> None:
        ...

    def get_formatted_votes(self, system: Optional[str] = ...) -> List[str]:
        ...

    def visualized_results(self, system: Optional[str] = ...) -> Optional[Union[bytes, str]]:
        ...

    @property
    def timestamp_str(self) -> Optional[str]:
        ...

    @property
    def all_votes(self: PollBase[_Numeric]) -> Dict[User, FullVoteBase[_Numeric]]:
        ...

    @property
    def all_votes_with_option_and_score(self: PollBase[_Numeric]) \
            -> List[Tuple[str, List[Vote], float]]:
        ...

    @property
    def partial_votes(self: PollBase[_Numeric]) -> Dict[User, FullVoteBase[_Numeric]]:
        ...

    @property
    def full_votes(self: PollBase[_Numeric]) -> Dict[User, FullVoteBase[_Numeric]]:
        ...

    @classmethod
    def get_electoral_system(cls: Type[PollBase[_Numeric]], system: Optional[str] = ...) \
            -> Type[electoral_system]:
        ...

    @classmethod
    def order_options(cls: Type[PollBase[_Numeric]], options: List[str],
                      votes: Dict[User, FullVoteBase[_Numeric]], system: Optional[str] = ...) \
            -> List[Tuple[str, List[Vote], float]]:
        ...

    @classmethod
    def visualize_options(cls: Type[PollBase[_Numeric]], question: str, options: List[str],
                          votes: Dict[User, FullVoteBase[_Numeric]], system: Optional[str] = ...) \
            -> Optional[Union[bytes, str]]:
        ...

    @classmethod
    def add(cls: Type[_Poll], channel: str, question: str, options: List[str]) -> _Poll:
        ...

    @classmethod
    def timestamped(cls: Type[_Poll], timestamp: str) -> _Poll:
        ...


def default_options_inner() -> List[Optional[_Numeric]]:
    ...


class FullVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...],  # noqa: N804
                attrs: Dict[str, Any]) -> Type[_FullVote]:
        ...


class FullVoteBase(models.Model, Generic[_Numeric], metaclass=FullVoteMeta):
    class Meta:
        abstract: bool
        ordering: Tuple[str, ...]
        indexes: Tuple[models.Index, ...]

    _state: ModelState
    poll_model: Type[PollBase[_Numeric]]
    poll: models.ForeignKey[PollBase[_Numeric], PollBase[_Numeric]]
    weights: List[Optional[_Numeric]]
    user: models.ForeignKey[User, User]
    user_secret: models.CharField[str, str]

    def save(self, *args: Any, **kwargs: Any) -> None:
        ...

    def get_form(self) -> forms.ModelForm:
        ...

    @property
    def options(self: FullVoteBase[_Numeric]) -> List[Tuple[str, Optional[_Numeric]]]:
        ...

    @classmethod
    def find_and_validate_if_exists(cls: Type[FullVoteBase[_Numeric]], poll: PollBase[_Numeric],
                                    user: User, user_secret: str) \
            -> Optional[FullVoteBase[_Numeric]]:
        ...

    @classmethod
    def find_and_validate_or_create_verified(cls: Type[_FullVote], poll: PollBase[_Numeric],
                                             user_name: str, user_secret: str) -> _FullVote:
        ...


class PartialVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...],  # noqa: N804
                attrs: Dict[str, Any]) -> Type[_PartialVote]:
        ...


class PartialVoteBase(models.Model, Generic[_Numeric], metaclass=PartialVoteMeta):
    class Meta:
        abstract: bool

    _state: ModelState
    poll_model: Type[PollBase[_Numeric]]
    poll: PollBase[_Numeric]
    user: models.ForeignKey[User, User]
    option: models.PositiveSmallIntegerField[int, int]
    weight: models.Field[_Numeric, _Numeric]

    def save(self, *args: Any, **kwargs: Any) -> None:
        ...

    @property
    def chosen_option(self) -> str:
        ...

    @classmethod
    def find_or_create(cls: Type[_PartialVote], poll: PollBase[_Numeric], user: User,
                       option: int) -> _PartialVote:
        ...
