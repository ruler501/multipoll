from django.db import models

from multipoll.models.pollbase import PollBase, FullVoteBase, PartialVoteBase, VForm


class MultiPoll(PollBase):
    class Meta(PollBase.Meta):
        proxy = True

    class PollMeta:
        weight_field = models.SmallIntegerField(null=False)

    supported_systems = ("approval", "borda")
    default_system = "borda"


class FullMultiVote(FullVoteBase):
    class Meta(FullVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll

    def get_form(self) -> VForm:
        return None


class PartialMultiVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll

    def get_form(self) -> VForm:
        return None