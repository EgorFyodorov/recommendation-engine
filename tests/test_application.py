import pytest

from recommendation_engine.application import RecommendItems, ValidationError
from recommendation_engine.domain import Recommendations, UserHistory


class FakeRecommendationEngine:
    def __init__(self) -> None:
        self.history: UserHistory | None = None

    def recommend(self, history: UserHistory) -> Recommendations:
        self.history = history
        return Recommendations(item_ids=(10, 20, 30))


def test_recommend_items_calls_engine_with_validated_history() -> None:
    engine = FakeRecommendationEngine()
    use_case = RecommendItems(engine)

    result = use_case.execute([1, 2, 3])

    assert result == [10, 20, 30]
    assert engine.history == UserHistory(item_ids=(1, 2, 3))


def test_recommend_items_rejects_empty_history() -> None:
    use_case = RecommendItems(FakeRecommendationEngine())

    with pytest.raises(ValidationError, match="must not be empty"):
        use_case.execute([])


@pytest.mark.parametrize("item_ids", [[-1], [10_000], [1, 2, 10_001]])
def test_recommend_items_rejects_out_of_range_item_ids(item_ids: list[int]) -> None:
    use_case = RecommendItems(FakeRecommendationEngine())

    with pytest.raises(ValidationError, match="range"):
        use_case.execute(item_ids)

