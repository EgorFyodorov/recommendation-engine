import pytest


def test_pytorch_model_returns_topk_item_ids() -> None:
    torch = pytest.importorskip("torch")

    from modeling.model import DEFAULT_NUM_RECOMMENDATIONS, Model

    model = Model()
    model.eval()

    with torch.no_grad():
        output = model(torch.tensor([1, 2, 3], dtype=torch.long))

    assert output.shape == (DEFAULT_NUM_RECOMMENDATIONS,)
    assert output.dtype == torch.long
