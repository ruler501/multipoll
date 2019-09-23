from typing import Optional, TypeVar
from typing import cast

from django import forms

from multipoll.forms.fullvotebase import FullVoteFormBase
from multipoll.models import FullApprovalVote

Numeric = TypeVar("Numeric")


class FullApprovalVoteForm(FullVoteFormBase):
    class Meta(FullVoteFormBase.Meta):
        abstract = False
        model = FullApprovalVote

    _method = forms.CharField(initial="approvalvote", widget=forms.HiddenInput())

    def sanitize_weight(self, weight: Optional[Numeric]) -> Optional[Numeric]:
        if weight is None or weight in ("off", 0, False, "false", "False", "f", ""):
            return cast(Numeric, False)
        else:
            return cast(Numeric, True)
