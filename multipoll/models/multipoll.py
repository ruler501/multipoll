from __future__ import annotations  # noqa: T499
# noqa: T499, E800

from typing import ClassVar, Dict, Tuple, Type

from django import forms
from django.db import models

from multipoll.models.pollbase import FullVoteBase, PartialVoteBase, PollBase


class MultiPoll(PollBase):
    WeightFieldType: ClassVar[Type['models.SmallIntegerField[int, int]']] = models.SmallIntegerField
    weight_field_args: ClassVar[Dict] = {'null': True}

    supported_systems: ClassVar[Tuple[str, ...]] = ("approval", "borda", "ranked_pairs",
                                                    "sum_score", "median_score", "mean_score",
                                                    "mean_score_infinity", "median_score_infinity",
                                                    "sum_score_infinity", "median_score_manhattan",
                                                    "sum_score_manhattan", "mean_score_manhattan")
    default_system: ClassVar[str] = "mean_score_infinity"

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        attach = {"name": "int_option", "text": self.options[ind], "type": "button",
                  "value": str(ind)}
        return attach


class FullMultiVote(FullVoteBase):
    class Meta(FullVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll

    def get_form(self) -> forms.ModelForm:
        import multipoll.forms
        return multipoll.forms.FullMultiVoteForm(instance=self)


class PartialMultiVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll
