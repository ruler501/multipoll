from django import forms
from django.core.exceptions import SuspiciousOperation
from django.http import QueryDict

from multipoll.models.approvalpoll import FullApprovalVote, ApprovalPoll


class FullApprovalVoteForm(forms.ModelForm):
    options = forms.MultipleChoiceField(choices=tuple(), required=False, widget=forms.CheckboxSelectMultiple())

    class Meta:
        model = FullApprovalVote
        fields = ('poll', 'user', 'user_secret')
        widgets = {
            'poll': forms.HiddenInput(),
            'user': forms.HiddenInput(),
            'user_secret': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            kwargs['data'] = args[0]
            args = tuple(args[1:])
        super().__init__(*args, **kwargs)
        if 'data' in kwargs:
            print(kwargs['data'])
            if 'poll' in kwargs['data']:
                setattr(self.instance, 'poll', ApprovalPoll.timestamped(kwargs['data']['poll']))
        if not self.instance.poll:
            raise SuspiciousOperation("Must define poll")
        self.fields['options'].choices = ((x, x) for x in self.instance.poll.options)
        if 'data' in kwargs and 'options' in kwargs['data']:
            options = kwargs['data']['options']
            if isinstance(kwargs['data'], QueryDict):
                options = kwargs['data'].getlist('options')
            print(f"kwargs.data.options {options}")
            self.instance.options = options
        self.options = self.instance.options
        print(self.options)

    # noinspection PyProtectedMember
    def save(self, commit=True):
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )
        existing = FullApprovalVote.validate_and_find_existing(self.instance.poll, self.instance.user,
                                                               self.instance.user_secret)
        if existing:
            self.instance = existing
        print(self.data['options'])
        self.instance.options = self.options
        print(self.instance.options)
        super().save(commit)

    def validate_unique(self):
        return True