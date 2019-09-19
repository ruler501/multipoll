from django import forms

from multipoll.forms.fullvotebase import FullVoteFormBase
from multipoll.models.approvalpoll import FullApprovalVote


class FullApprovalVoteForm(FullVoteFormBase):
    _method = forms.CharField(initial="approvalvote", widget=forms.HiddenInput())

    class Meta(FullVoteFormBase.Meta):
        abstract = False
        model = FullApprovalVote