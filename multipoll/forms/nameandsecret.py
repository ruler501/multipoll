import random

from django import forms
from wn import NOUN, ADJ, WordNet
from wn.constants import wordnet_30_dir  # noqa


def get_default_secret(max_word_length: int = 4) -> str:
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
    user_secret = forms.CharField(label="Secret (Default is randomly generated, can be blank. Used to verify when "
                                        + "changing responses; not securely stored):", max_length=11,
                                  required=False, initial=get_default_secret)
