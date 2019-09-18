from typing import List, Tuple

from django.db import models

from multipoll.models.pollbase import PollBase, FullVoteBase, PartialVoteBase, Vote
from multipoll.utils import absolute_url_without_request, Numeric


class ApprovalPoll(PollBase):
    class Meta(PollBase.Meta):
        abstract = False

    class PollMeta:
        weight_field = models.BooleanField(null=False)

    supported_systems = ("approval",)
    default_system = "approval"\

    @property
    def full_votes(self) -> List[List[Vote]]:
        votes: List[List[Vote]] = [[] for _ in self.options]
        vote: FullVoteBase
        for vote in self.fullvote_set.all():
            for option in vote.options:
                ind = self.options.index(option)
                votes[ind].append((vote.user, True))
        votes = [sorted(option, key=lambda v: v[0].name) for option in votes]
        return votes

    def get_absolute_url(self):
        if self.timestamp:
            return absolute_url_without_request(f"/polls/{self.timestamp_str}/")
        else:
            return None

    @property
    def formatted_votes(self) -> List[str]:
        options_with_votes = self.order_options(self.options, self.all_votes)
        votes = list(zip(*options_with_votes))[1]
        print(votes)
        # noinspection PyTypeChecker
        return [f"({self.calculate_weight(i, votes)}) {ovs[0]} ({', '.join([u.name for u, _ in ovs[1]])})"
                for i, ovs in enumerate(options_with_votes)]


class FullApprovalVote(FullVoteBase):
    class Meta(FullVoteBase.Meta):
        abstract = False

    poll_model = ApprovalPoll

    @property
    def options(self) -> List[str]:
        return [o for o, w in super().options if w]

    @options.setter
    def options(self, value: List[str]) -> None:
        values = self.poll.options
        self.weights = [(v in value) for v in values]


class PartialApprovalVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = ApprovalPoll