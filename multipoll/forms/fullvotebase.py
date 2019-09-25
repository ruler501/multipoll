from __future__ import annotations  # noqa: T484

from typing import Any, Generic, List, Optional, Type, TypeVar, Union
from typing import cast

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import SuspiciousOperation

from multipoll.models.pollbase import FullVoteBase, PollBase
from multipoll.models.user import User
from multipoll.utils import ClassProperty

Numeric = TypeVar('Numeric')
Poll = TypeVar('Poll', bound=PollBase)
FullVote = TypeVar('FullVote', bound=FullVoteBase, covariant=True)
FullVoteForm = TypeVar("FullVoteForm", bound='FullVoteFormBase')


class FullVoteFormBase(forms.ModelForm, Generic[Numeric]):
    class Meta(Generic[FullVote]):
        vote_model: Type[FullVote]
        abstract = True
        fields = ('poll', 'user', 'user_secret')
        widgets = {
            'poll': forms.HiddenInput(),
            'user': forms.HiddenInput(),
            'user_secret': forms.HiddenInput()
        }

    instance: FullVoteBase[Numeric]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if len(args) > 0:
            kwargs['data'] = args[0]
            args = tuple(args[1:])
        super(FullVoteFormBase, self).__init__(*args, **kwargs)
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data']
            poll = self.poll_model.timestamped(data['poll'])
            self.instance.poll = poll
            user_name = data['user']
            user = User.find_or_create(user_name)
            self.instance = \
                self.vote_model.find_and_validate_or_create_verified(poll, user,
                                                                     data["user_secret"])
        if not self.instance.poll:
            raise SuspiciousOperation("Must define poll")
        # noinspection PyUnresolvedReferences
        options = self.instance.poll.options
        vote_list = self.instance.poll.all_votes.values()
        for vote in vote_list:
            if vote.user == self.instance.user:
                weights = vote.weights
                break
        else:
            weights = [None for _ in options]
        array_field: ArrayField = self.vote_model._meta.get_field('weights')
        weight_field = array_field.base_field
        for i, wo in enumerate(zip(weights, options)):
            w, o = wo
            field_kwargs = {"required": False, "label": o}
            if w is not None:
                field_kwargs["initial"] = o
            self.fields[f"option-{i}"] = weight_field.formfield(**field_kwargs)

    def save(self, commit: bool = True) -> None:
        if self.errors:
            # noinspection PyProtectedMember
            if self.instance._state.adding:
                added = 'created'
            else:
                added = 'changed'
            # noinspection PyProtectedMember
            # noinspection PyUnresolvedReferences
            raise ValueError(
                f"The {self.instance._meta.object_name} could not be "
                + f"{added} because the data didn't validate."
            )
        existing = self.vote_model.find_and_validate_if_exists(self.instance.poll,
                                                               self.instance.user,
                                                               self.instance.user_secret)
        if existing:
            self.instance = existing
        weights: List[Optional[Numeric]] = [None for _ in range(self.poll_model.MAX_OPTIONS)]
        for field_name in self.fields:
            if field_name.startswith("option"):
                ind = int(field_name[len("option-"):])
                weights[ind] = self.sanitize_weight(self.data.get(field_name, None))
        self.instance.weights = weights
        # noinspection PyUnresolvedReferences
        return super(FullVoteFormBase, self).save(commit)

    # noinspection PyMethodMayBeStatic
    def sanitize_weight(self, weight: Optional[Union[str, Numeric]]) -> Optional[Numeric]:
        if weight == "":
            return None
        else:
            return cast(Numeric, weight)

    # noinspection PyMethodMayBeStatic
    def validate_unique(self) -> None:
        self.vote_model.find_and_validate_if_exists(self.instance.poll, self.instance.user,
                                                    self.instance.user_secret)

    # noinspection PyMethodParameters
    @ClassProperty
    def vote_model(cls) -> Type[FullVoteBase[Numeric]]:  # noqa: N805
        return getattr(getattr(cls, "Meta"), "model")

    # noinspection PyMethodParameters
    @ClassProperty
    def poll_model(cls) -> Type[PollBase[Numeric]]:  # noqa: N805
        return getattr(getattr(cls, "vote_model"), "poll_model")
