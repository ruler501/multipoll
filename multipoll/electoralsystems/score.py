from __future__ import annotations  # noqa

from typing import List
from typing import TYPE_CHECKING

from multipoll.electoralsystems.utils import electoral_system
from multipoll.electoralsystems.utils.cardinalscores import normalize_scores, \
    normalize_scores_with_fixed_max_ints

if TYPE_CHECKING:
    import multipoll.models  # noqa: E402


class score(electoral_system):  # noqa: N801
    key = "score"
    label = "Score"

    @classmethod
    def generate_scores(cls, votes: List[multipoll.models.FullVoteBase]) -> List[float]:
        if len(votes) == 0:
            return []
        all_scores = [normalize_scores(v.weights[len(v.options)], 2) for v in votes]
        scores = [sum((s[i] or 0 for s in all_scores)) for i in range(len(votes[0].options))]
        return normalize_scores_with_fixed_max_ints(scores)