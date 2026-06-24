from collections.abc import Sequence

from recommendation_engine.application.errors import ValidationError
from recommendation_engine.domain import RecommendationEngine, UserHistory


class RecommendItems:
    def __init__(self, recommender: RecommendationEngine, catalog_size: int = 10_000) -> None:
        self._recommender = recommender
        self._catalog_size = catalog_size

    def execute(self, item_ids: Sequence[int]) -> list[int]:
        history = UserHistory(self._validate_item_ids(item_ids))
        recommendations = self._recommender.recommend(history)
        return list(recommendations.item_ids)

    def _validate_item_ids(self, item_ids: Sequence[int]) -> tuple[int, ...]:
        ids = tuple(int(item_id) for item_id in item_ids)

        if not ids:
            raise ValidationError("item_ids must not be empty")

        invalid_ids = [
            item_id for item_id in ids if item_id < 0 or item_id >= self._catalog_size
        ]
        if invalid_ids:
            preview = ", ".join(str(item_id) for item_id in invalid_ids[:5])
            raise ValidationError(
                f"item_ids must be in range [0, {self._catalog_size - 1}], got: {preview}"
            )

        return ids

