from __future__ import annotations  # noqa: T499
# noqa: T499, E800

import logging
from typing import Any, Generic, List, Optional, Type, TypeVar, Union
from typing import cast

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import SuspiciousOperation

from multipoll.models.pollbase import FullVoteBase, PollBase
from multipoll.models.user import User
from multipoll.utils import classproperty

logger = logging.getLogger(__name__)


Poll = TypeVar('Poll', bound=PollBase)
FullVote = TypeVar('FullVote', bound=FullVoteBase, covariant=True)
FullVoteForm = TypeVar("FullVoteForm", bound='FullVoteFormBase')


class FullVoteFormBase(forms.ModelForm):
    class Meta(Generic[FullVote]):
        vote_model: Type[FullVote]
        abstract = True
        fields = ('poll', 'user', 'user_secret')
        widgets = {
            'poll': forms.HiddenInput(),
            'user': forms.HiddenInput(),
            'user_secret': forms.HiddenInput()
        }

    instance: FullVoteBase

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if len(args) > 0:
            kwargs['data'] = args[0]
            args = tuple(args[1:])
        super(FullVoteFormBase, self).__init__(*args, **kwargs)
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data']
            logger.info(f"FulLVoteFormBase fromPOST: loading poll {data['poll']} as "
                        + f"{self.poll_model}")
            poll = self.poll_model.timestamped(data['poll'])
            self.instance.poll = poll
            logger.info("FullVoteFormBase fromPOST: successfully loaded poll")
            user_name = data['user']
            logger.info(f"FullVoteFormBase fromPOST: loading user with username: {user_name}")
            user = User.find_or_create(user_name)
            logger.info(f"FullVoteFormBase fromPOST: finished loading user, creating vote model: "
                        + f"{poll}, {user}, {data['user_secret']}")
            self.instance = \
                self.vote_model.find_and_validate_or_create_verified(poll, user,
                                                                     data["user_secret"])
            if not self.instance or not self.instance.poll:
                raise SuspiciousOperation("Must define poll")
            options = self.instance.poll.options
            weights: List[Optional[int]] = [None for _ in options]
            for i in range(len(options)):
                if f'option-{i}' in data:
                    weights[i] = int(data[f'option-{i}'])
        else:
            vote_list = self.instance.poll.all_votes.values()
            for vote in vote_list:
                if vote.user == self.instance.user:
                    weights = vote.weights
                    break
        logger.info("Found properties")
        array_field: ArrayField = self.vote_model._meta.get_field('weights')
        weight_field = array_field.base_field
        for i, wo in enumerate(zip(weights, options)):
            w, o = wo
            field_kwargs = {"required": False, "label": o}
            if w is not None:
                field_kwargs["initial"] = o
            self.fields[f"option-{i}"] = weight_field.formfield(**field_kwargs)
        logger.info("Populated fields")

    def save(self, commit: bool = True) -> None:
        if self.errors:
            if self.instance._state.adding:
                added = 'created'
            else:
                added = 'changed'
            raise ValueError(
                f"The {self.instance._meta.object_name} could not be "
                + f"{added} because the data didn't validate."
            )
        existing = self.vote_model.find_and_validate_if_exists(self.instance.poll,
                                                               self.instance.user,
                                                               self.instance.user_secret)
        if existing:
            self.instance = existing
        weights: List[Optional[int]] = [None for _ in range(self.poll_model.MAX_OPTIONS)]
        for field_name in self.fields:
            if field_name.startswith("option"):
                ind = int(field_name[len("option-"):])
                weights[ind] = self.sanitize_weight(self.data.get(field_name, None))
        self.instance.weights = weights
        return super(FullVoteFormBase, self).save(commit)

    def sanitize_weight(self, weight: Optional[Union[str, int]]) -> Optional[int]:
        if weight == "":
            return None
        else:
            return cast(int, weight)

    def validate_unique(self) -> None:
        self.vote_model.find_and_validate_if_exists(self.instance.poll, self.instance.user,
                                                    self.instance.user_secret)

    @classproperty
    def vote_model(cls) -> Type[FullVoteBase]:  # noqa: N805
        return getattr(getattr(cls, "Meta"), "model")

    @classproperty
    def poll_model(cls) -> Type[PollBase]:  # noqa: N805
        return getattr(getattr(cls, "vote_model"), "poll_model")
