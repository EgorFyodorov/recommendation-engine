from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UserHistory:
    item_ids: tuple[int, ...]


@dataclass(frozen=True)
class Recommendations:
    item_ids: tuple[int, ...]


class RecommendationEngine(Protocol):
    def recommend(self, history: UserHistory) -> Recommendations:
        ...
