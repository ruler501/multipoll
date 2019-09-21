from typing import List, Dict

from django.db import models

from multipoll.models.pollbase import PollBase, FullVoteBase, PartialVoteBase, Vote, VForm


class ApprovalPoll(PollBase):
    class PollMeta:
        weight_field = models.BooleanField(null=True)

    supported_systems = ("approval",)
    default_system = "approval"\

    @property
    def full_votes(self) -> List[List[Vote]]:
        votes: List[List[Vote]] = [[] for _ in self.options]
        vote: FullApprovalVote
        for vote in getattr(self, getattr(self, "FullVoteType").name.lower() + "_set").all():
            for option in vote.options: 
                ind = self.options.index(option)
                votes[ind].append((vote.user, True))
        votes = [sorted(option, key=lambda v: v[0].name) for option in votes]
        return votes

    @property
    def formatted_votes(self) -> List[str]:
        return [f"({'' if s is None else s}) {o} "
                + f"({', '.join([u.name for u, w in votes if w])})"
                for o, votes, s in self.all_votes_with_option_and_score]

    def create_attachment_for_option(self, ind: int) -> Dict[str, str]:
        attach = {"name": "bool_option", "text": self.options[ind], "type": "button", "value": str(ind)}
        return attach


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

    def get_form(self) -> VForm:
        from multipoll.forms import FullApprovalVoteForm
        return FullApprovalVoteForm(instance=self)


class PartialApprovalVote(PartialVoteBase):
    class Meta(PartialVoteBase.Meta):
        abstract = False

    poll_model = ApprovalPoll