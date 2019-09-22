import logging
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.base import ModelBase

from typedmodels.models import TypedModel

from multipoll.models.fields import TimestampField
from multipoll.models.user import User

Numeric = TypeVar('Numeric')
NumericContra = TypeVar('NumericContra', contravariant=True)
NumericCov = TypeVar('NumericCov', covariant=True)
OptNumeric = Optional[Numeric]
OptNumericContra = Optional[NumericContra]
Vote = Tuple[User, OptNumeric]
MForm = TypeVar('MForm', bound=forms.ModelForm, covariant=True)
Poll = TypeVar('Poll', bound='PollBase')
PollContra = TypeVar('PollContra', bound='PollBase', contravariant=True)
PollCov = TypeVar('PollCov', bound='PollBase', covariant=True)
FullVote = TypeVar('FullVote', bound='FullVoteBase')
FullVoteContra = TypeVar('FullVoteContra', bound='FullVoteBase', contravariant=True)
FullVoteCov = TypeVar('FullVoteCov', bound='FullVoteBase', covariant=True)
PartialVote = TypeVar('PartialVote', bound='PartialVoteBase')
PartialVoteContra = TypeVar('PartialVoteContra', bound='PartialVoteBase', contravariant=True)
PartialVoteCov = TypeVar('PartialVoteCov', bound='PartialVoteBase', covariant=True)

logger = logging.getLogger(__name__)


class PollBase(TypedModel, Generic[NumericContra]):
    FullVoteType: Type[FullVoteBase[NumericContra]]
    PartialVoteType: Type[PartialVoteBase[NumericContra]]
    timestamp: TimestampField
    channel: models.CharField[str, str]
    question: models.CharField[str, str]
    options: ArrayField[List[str], List[str]]
    class Meta:
        get_latest_by: str
        ordering: Tuple[str, ...]
        indexes: Tuple[models.Index, ...]

    supported_systems: Tuple[str, ...]
    default_system: str

    @property
    def timestamp_str(self) -> Optional[str]: ...
    @property
    def all_votes(self) -> Dict[User, FullVote]: ...
    @property
    def all_votes_with_option_and_score(self) -> List[Tuple[str, List[Vote], float]]: ...
    @property
    def formatted_votes(self) -> List[str]: ...
    @property
    def partial_votes(self) -> Dict[User, FullVote]: ...
    @property
    def full_votes(self) -> Dict[User, FullVote]: ...
    @classmethod
    def order_options(cls: Type[Poll], options: List[str],
                      votes: Dict[User, FullVote]) -> List[Tuple[str, List[Vote], float]]: ...
    def get_absolute_url(self) -> Optional[str]: ...
    def create_attachment_for_option(self, ind: int) -> Dict[str, str]: ...
    def format_attachments(self, include_add_more: bool = True) -> str: ...
    @classmethod
    def add(cls: Type[Poll], channel: str, question: str, options: List[str]) -> Poll: ...
    @classmethod
    def timestamped(cls: Type[Poll], timestamp: str) -> Poll: ...
    def post_poll(self) -> None: ...
    def update_poll(self) -> None: ...
    def save(self, *args: Any, **kwargs: Any) -> None: ...

def default_options_inner() -> List[OptNumeric]: ...


class FullVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...],
                attrs: Dict[str, Any]) -> Type[FullVoteContra]: ...


class FullVoteBase(models.Model, Generic[NumericContra], metaclass=FullVoteMeta):
    poll_model: Type[PollBase[NumericContra]]
    poll: models.ForeignKey[PollBase[NumericContra], PollBase[NumericContra]]
    weights: List[Optional[NumericContra]]
    user: models.ForeignKey[User, User]
    user_secret: models.CharField[str, str]
    MAX_OPTIONS: int

    class Meta:
        abstract: bool
        ordering: Tuple[str, ...]
        indexes: Tuple[models.Index, ...]

    @property
    def options(self) -> List[Tuple[str, OptNumericContra]]: ...
    def save(self, *args: Any, **kwargs: Any) -> None: ...
    def get_form(self) -> forms.ModelForm: ...
    @classmethod
    def find_and_validate_if_exists(cls, poll: PollContra, user: User,
                                    user_secret: str) -> Optional[FullVoteContra]: ...
    @classmethod
    def find_and_validate_or_create_verified(cls: Type[FullVote], poll: Poll, user_name: str,
                                             user_secret: str) -> FullVote: ...


class PartialVoteMeta(ModelBase):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any])\
            -> Type[PartialVote]: ...


class PartialVoteBase(models.Model, Generic[NumericContra], metaclass=PartialVoteMeta):
    poll_model: Type[PollBase[NumericContra]]
    poll: PollBase[NumericContra]
    user: models.ForeignKey[User, User]
    option: models.PositiveSmallIntegerField[int, int]
    weight: models.Field[NumericContra, NumericContra]

    class Meta:
        abstract: bool

    @property
    def chosen_option(self) -> str: ...
    def save(self, *args: Any, **kwargs: Any) -> None: ...
    @classmethod
    def find_or_create(cls: Type[PartialVote], poll: PollContra, user: User,
                       option: int) -> PartialVote: ...