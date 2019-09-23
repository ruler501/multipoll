from multipoll.electoralsystems.approval import approval
from multipoll.electoralsystems.borda import borda
from multipoll.electoralsystems.ranking import Ranking
from multipoll.electoralsystems.registry import electoral_system, get_electoral_system


__all__ = ["electoral_system", "Ranking", "get_electoral_system", "approval", "borda"]