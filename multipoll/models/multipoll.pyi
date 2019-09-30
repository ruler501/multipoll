from __future__ import annotations  # noqa: T499
# noqa: T499, E800

from typing import Any, Dict, Tuple, Type

from django.db import models

import multipoll.forms
from multipoll.models.pollbase import FullVoteBase, PartialVoteBase, PollBase


class MultiPoll(PollBase[int]):
    WeightFieldType: Type[models.SmallIntegerField[int, int]]
    weight_field_args: Dict[str, Any]

    supported_systems: Tuple[str, ...]
    default_system: str

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        ...


class FullMultiVote(FullVoteBase[int]):
    class Meta(FullVoteBase.Meta):
        abstract: bool

    poll_model: Type[MultiPoll]

    def get_form(self) -> multipoll.forms.FullMultiVoteForm:
        ...


class PartialMultiVote(PartialVoteBase[int]):
    class Meta(PartialVoteBase.Meta):
        abstract: bool

    poll_model: Type[MultiPoll]
