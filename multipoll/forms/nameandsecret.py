import random
from typing import Dict, List, Tuple

from django import forms

from wn import ADJ, NOUN
from wn import WordNet
from wn.constants import wordnet_30_dir


def get_default_secret(max_word_length: int = 4) -> str:
    if max_word_length not in _words:
        nouns = [n for n in _wordnet.all_lemma_names(NOUN)
                 if n.isalpha() and len(n) <= max_word_length]
        adjectives = [a for a in _wordnet.all_lemma_names(ADJ)
                      if a.isalpha() and len(a) <= max_word_length]
        _words[max_word_length] = (nouns, adjectives)
    nouns, adjectives = _words[max_word_length]
    return random.choice(adjectives) + ' ' + random.choice(nouns)


_wordnet = WordNet(wordnet_30_dir)
_words: Dict[int, Tuple[List[str], List[str]]] = {}


class NameAndSecretForm(forms.Form):
    user_name = forms.CharField(label="Your Name:", min_length=2, max_length=30, required=True)
    user_secret = forms.CharField(label="Secret (Default is randomly generated, can be blank. Used "
                                        + "to verify when changing responses; not securely "
                                        + "stored):",
                                  max_length=11, required=False, initial=get_default_secret)