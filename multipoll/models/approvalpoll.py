from __future__ import annotations  # noqa: T499
# noqa: T499, E800

from typing import Dict, List, Optional, Tuple, Type

from django import forms
from django.db import models

from multipoll.models.pollbase import FullVoteBase, PartialVoteBase, PollBase
from multipoll.utils import FALSEY_VALUES


class ApprovalPoll(PollBase):
    WeightFieldType: Type['models.BooleanField[Optional[bool], Optional[bool]]'] = \
        models.BooleanField
    weight_field_args = {"null": True}

    supported_systems = ("approval",)
    default_system = "approval"

    def get_formatted_votes(self, system: Optional[str] = None) -> List[str]:
        return [f"({'' if s is None else s}) {o} "  # noqa: IF100
                + f"({', '.join([u.name for u, w in votes if w and w not in FALSEY_VALUES])})"
                for o, votes, s in self.all_votes_with_option_and_score]

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        attach = {"name": "bool_option", "text": self.options[ind], "type": "button",
                  "value": str(ind)}
        return attach


class FullApprovalVote(FullVoteBase):
    class Meta(FullVoteBase.Meta):
        abstract = False

    poll_model = ApprovalPoll

    @property
    def options(self) -> List[Tuple[str, Optional[bool]]]:
        return [(o, w) for o, w in super(FullApprovalVote, self).options if w]

    @options.setter
    def options(self, value: List[str]) -> None:
        values = self.poll.options
        self.weights = [(v in value) for v in values]

    def get_form(self) -> forms.ModelForm:
        import multipoll.forms
        return multipoll.forms.FullApprovalVoteForm(instance=self)


class PartialApprovalVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = ApprovalPoll
