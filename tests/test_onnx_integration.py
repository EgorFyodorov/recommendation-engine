import pytest


def test_exported_onnx_matches_pytorch(tmp_path) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("onnx")
    pytest.importorskip("onnxruntime")

    from modeling.export_onnx import export_onnx
    from modeling.verify_onnx import verify_onnx

    model_path = tmp_path / "recommendation-engine.onnx"

    export_onnx(model_path)
    results = verify_onnx(model_path)

    assert len(results) > 0


def test_onnx_adapter_returns_recommendation_ids(tmp_path) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("onnx")
    pytest.importorskip("onnxruntime")

    from modeling.export_onnx import export_onnx
    from recommendation_engine.domain import UserHistory
    from recommendation_engine.infrastructure import OnnxRecommendationEngine

    model_path = tmp_path / "recommendation-engine.onnx"
    export_onnx(model_path)
    engine = OnnxRecommendationEngine(model_path)

    recommendations = engine.recommend(UserHistory(item_ids=(1, 2, 3)))

    assert len(recommendations.item_ids) == 10
    assert all(isinstance(item_id, int) for item_id in recommendations.item_ids)
