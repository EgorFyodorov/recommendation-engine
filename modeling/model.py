import torch

DEFAULT_NUM_ITEMS = 10_000
DEFAULT_EMBEDDING_DIM = 32
DEFAULT_NUM_RECOMMENDATIONS = 10


class Model(torch.nn.Module):
    def __init__(
        self,
        num_recommendations: int = DEFAULT_NUM_RECOMMENDATIONS,
        device: str = "cpu",
    ) -> None:
        super().__init__()
        self._item_embeddings = torch.rand(
            (DEFAULT_NUM_ITEMS, DEFAULT_EMBEDDING_DIM),
            device=device,
        )
        self._num_recommendations = num_recommendations

    def forward(self, user_history: torch.Tensor) -> torch.Tensor:
        user_embedding = self._item_embeddings[user_history].mean(axis=0)
        scores = user_embedding @ self._item_embeddings.T
        topk = torch.topk(scores, k=self._num_recommendations)
        return topk.indices
