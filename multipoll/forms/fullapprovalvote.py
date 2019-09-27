from typing import Optional

from django import forms

from multipoll.forms.fullvotebase import FullVoteFormBase
from multipoll.models import FullApprovalVote


class FullApprovalVoteForm(FullVoteFormBase[bool]):
    class Meta(FullVoteFormBase.Meta):
        abstract = False
        model = FullApprovalVote

    _method = forms.CharField(initial="approvalvote", widget=forms.HiddenInput())

    def sanitize_weight(self, weight: Optional[bool]) -> bool:
        if weight is None or weight in ("off", 0, False, "false", "False", "f", ""):
            return False
        else:
            return True
