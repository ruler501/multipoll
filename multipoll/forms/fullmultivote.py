from django import forms

from multipoll.forms.fullvotebase import FullVoteFormBase
from multipoll.models import FullMultiVote


class FullMultiVoteForm(FullVoteFormBase):
    class Meta(FullVoteFormBase.Meta):
        abstract = False
        model = FullMultiVote

    _method = forms.CharField(initial="multivote", widget=forms.HiddenInput())