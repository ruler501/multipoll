from __future__ import annotations  # noqa: T499
# noqa: T499, E800

from typing import Dict, Type

from django import forms
from django.db import models

from multipoll.models.pollbase import FullVoteBase, PartialVoteBase, PollBase


class MultiPoll(PollBase):
    WeightFieldType: Type['models.SmallIntegerField[int, int]'] = models.SmallIntegerField
    weight_field_args = {'null': True}

    supported_systems = ("approval", "borda", "rankedpairs")
    default_system = "rankedpairs"

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        attach = {"name": "numeric_option", "text": self.options[ind], "type": "button",
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
