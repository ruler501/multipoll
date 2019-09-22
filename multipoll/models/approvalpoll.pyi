from typing import Any, Dict, List, Optional, Tuple, Type

from django.db import models

import multipoll.forms
from multipoll.models.pollbase import FullVoteBase, PartialVoteBase, PollBase


class ApprovalPoll(PollBase[bool]):
    WeightFieldType: Type['models.BooleanField[Optional[bool], Optional[bool]]']
    weight_field_args: Dict[str, Any]
    supported_systems: Tuple[str, ...]
    default_system: str

    @property
    def formatted_votes(self) -> List[str]: ...
    def create_attachment_for_option(self, ind: int) -> Dict[str, str]: ...


class FullApprovalVote(FullVoteBase[bool]):
    class Meta(FullVoteBase.Meta):
        abstract: bool

    poll_model: Type[ApprovalPoll]

    @property
    def options(self) -> List[Tuple[str, Optional[bool]]]: ...
    @options.setter
    def options(self, value: List[str]) -> None: ...
    def get_form(self) -> multipoll.forms.FullApprovalVoteForm: ...


class PartialApprovalVote(PartialVoteBase[bool]):
    class Meta(PartialVoteBase.Meta):
        abstract: bool
    poll_model: Type[ApprovalPoll]