from django.db import models

from multipoll.models.pollbase import PollBase, FullVoteBase, PartialVoteBase
from multipoll.utils import absolute_url_without_request


class MultiPoll(PollBase):
    class Meta(PollBase.Meta):
        abstract = False

    class PollMeta:
        weight_field = models.SmallIntegerField(null=False)

    supported_systems = ("approval", "borda")
    default_system = "borda"

    def get_absolute_url(self):
        if self.timestamp:
            return absolute_url_without_request(f"/mpolls/{self.timestamp_str}/")
        else:
            return None


class FullMultiVote(FullVoteBase):
    class Meta(FullVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll


class PartialMultiVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = MultiPoll