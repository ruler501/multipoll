import random
from typing import Any, Dict

from django import forms
from django.core.exceptions import ValidationError
from django.http import QueryDict

from wn import WordNet
from wn.constants import wordnet_30_dir, NOUN, ADJ

from main.models import CompleteVote, Poll, validate_vote


def get_default_secret(max_word_length: int = 4):
    if max_word_length not in get_default_secret.words:
        nouns = [n for n in get_default_secret.wordnet.all_lemma_names(NOUN)
                 if n.isalpha() and len(n) <= max_word_length]
        adjectives = [a for a in get_default_secret.wordnet.all_lemma_names(ADJ)
                      if a.isalpha() and len(a) <= max_word_length]
        get_default_secret.words[max_word_length] = (nouns, adjectives)
    nouns, adjectives = get_default_secret.words[max_word_length]
    return random.choice(adjectives) + ' ' + random.choice(nouns)


get_default_secret.wordnet = WordNet(wordnet_30_dir)
get_default_secret.words = {}


class NameAndSecretForm(forms.Form):
    user_name = forms.CharField(label="Your Name:", min_length=2, max_length=30, required=True)
    user_secret = forms.CharField(label="Secret (Default is randomly generated or input your own, these not stored in "
                                         + "a cryptographically sound manner so do not use a password from another "  # noqa
                                         + "site):", max_length=11,
                                  required=False, initial=get_default_secret)


class MultipleChoiceCompleteVoteForm(forms.ModelForm):
    options = forms.MultipleChoiceField(choices=tuple(), required=False, widget=forms.CheckboxSelectMultiple())

    class Meta:
        model = CompleteVote
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
                setattr(self.instance, 'poll', Poll.objects.get(timestamp=kwargs['data']['poll']))
        if not self.instance.poll:
            raise ValidationError("Must define poll")
        self.fields['options'].choices = ((x, x) for x in self.instance.poll.options)
        if 'data' in kwargs and 'options' in kwargs['data']:
            options = kwargs['data']['options']
            if isinstance(kwargs['data'], QueryDict):
                options = kwargs['data'].getlist('options')
            print(f"kwargs.data.options {options}")
            self.instance.options = options
        self.options = self.instance.options
        print(self.options)

    def save(self, commit=True):
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )
        existing = validate_vote(self.instance.poll, self.instance.user, self.instance.user_secret)
        if existing:
            self.instance = existing
        print(self.data['options'])
        self.instance.options = self.options
        print(self.instance.options)
        super().save(commit)

    def validate_unique(self):
        return True