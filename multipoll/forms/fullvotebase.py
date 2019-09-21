from typing import Type, TypeVar, Dict, List

from django import forms
from django.core.exceptions import SuspiciousOperation

from multipoll.models import Poll, FullVote, User
from multipoll.utils import ClassProperty, OptNumeric

FormField = TypeVar('FormField', bound=forms.Field)


class FullVoteFormBase(forms.ModelForm):
    fields: Dict[str, FormField]
    errors: bool
    instance: FullVote

    # noinspection PyMethodParameters
    @ClassProperty
    def vote_model(cls: Type['FullVoteForm']) -> Type['Poll']:
        return getattr(getattr(cls, "Meta"), "model")

    # noinspection PyMethodParameters
    @ClassProperty
    def poll_model(cls: Type['FullVoteForm']) -> Type['Poll']:
        return getattr(getattr(cls, "vote_model"), "poll_model")

    class Meta:
        vote_model: Type['FullVote']
        abstract = True
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
        if 'data' in kwargs and 'poll' in kwargs['data']:
            poll = self.poll_model.timestamped(kwargs['data']['poll'])
            setattr(self.instance, 'poll', poll)
            user_name = kwargs['data']['user']
            user = User.find_or_create(user_name)
            existing = self.vote_model.validate_and_find_existing(poll, user, kwargs["data"]["user_secret"])
            if existing:
                self.instance = existing
        if not self.instance.poll:
            raise SuspiciousOperation("Must define poll")
        # noinspection PyUnresolvedReferences
        options = self.instance.poll.options
        vote_list = self.instance.poll.all_votes
        for vote in vote_list:
            if vote.user == self.instance.user:
                weights = vote.weights
                break
        else:
            weights = [None for _ in options]
        for i, wo in enumerate(zip(weights, options)):
            w, o = wo
            if w is None:
                self.fields[f"option-{i}"] = getattr(getattr(self.poll_model, "PollMeta"),
                                                     "weight_field").formfield(required=False,
                                                                               label=o)
            else:
                self.fields[f"option-{i}"] = getattr(getattr(self.poll_model, "PollMeta"),
                                                     "weight_field").formfield(required=False,
                                                                               label=o, initial=w)

    def save(self, commit=True):
        if self.errors:
            # noinspection PyProtectedMember
            # noinspection PyUnresolvedReferences
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )
        existing = self.vote_model.validate_and_find_existing(self.instance.poll, self.instance.user,
                                                              self.instance.user_secret)
        if existing:
            self.instance = existing
        weights: List[OptNumeric] = [None for _ in range(self.poll_model.MAX_OPTIONS)]
        for field_name in self.fields:
            if field_name.startswith("option"):
                ind = int(field_name[len("option-"):])
                weights[ind] = self.sanitize_weight(self.data.get(field_name, None))
        self.instance.weights = weights
        print(weights)
        # noinspection PyUnresolvedReferences
        return super().save(commit)

    # noinspection PyMethodMayBeStatic
    def sanitize_weight(self, weight: OptNumeric) -> OptNumeric:
        if weight == "":
            return None
        else:
            return weight

    # noinspection PyMethodMayBeStatic
    def validate_unique(self):
        return True


FullVoteForm = TypeVar("FullVoteForm", bound=FullVoteFormBase)
