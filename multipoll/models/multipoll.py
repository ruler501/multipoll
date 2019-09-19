from typing import Type, Dict

from django.db import models

from multipoll.models.pollbase import PollBase, FullVoteBase, PartialVoteBase, VForm


class MultiPoll(PollBase):
    class PollMeta:
        weight_field = models.SmallIntegerField(null=True)

    supported_systems = ("approval", "borda")
    default_system = "borda"

    @classmethod
    def create_attachment_for_option(cls: Type['MultiPoll'], option: str) -> Dict[str, str]:
        attach = {"name": "numeric_option", "text": option, "type": "button", "value": option}
        return attach


class FullMultiVote(FullVoteBase):
    class Meta(FullVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll

    def get_form(self) -> VForm:
        from multipoll.forms import FullMultiVoteForm
        return FullMultiVoteForm(instance=self)


class PartialMultiVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll

    def get_form(self) -> VForm:
        return None