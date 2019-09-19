from django import forms

from multipoll.forms.fullvotebase import FullVoteFormBase
from multipoll.models.approvalpoll import FullApprovalVote
from multipoll.utils import OptNumeric


class FullApprovalVoteForm(FullVoteFormBase):
    _method = forms.CharField(initial="approvalvote", widget=forms.HiddenInput())

    class Meta(FullVoteFormBase.Meta):
        abstract = False
        model = FullApprovalVote

    def sanitize_weight(self, weight: OptNumeric) -> OptNumeric:
        if weight is None or weight in ("off", 0, False, "false", "False", "f"):
            return False
        else:
            return True