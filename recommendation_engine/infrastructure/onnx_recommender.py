from pathlib import Path

import numpy as np

from recommendation_engine.domain import Recommendations, UserHistory


class OnnxRecommendationEngine:
    def __init__(
        self,
        model_path: str | Path,
        input_name: str = "user_history",
        output_name: str = "recommendations",
        providers: list[str] | None = None,
    ) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"ONNX model does not exist: {model_path}")

        import onnxruntime as ort

        self._session = ort.InferenceSession(
            str(model_path),
            providers=providers or ["CPUExecutionProvider"],
        )
        self._input_name = input_name
        self._output_name = output_name

    def recommend(self, history: UserHistory) -> Recommendations:
        user_history = np.asarray(history.item_ids, dtype=np.int64)
        output = self._session.run([self._output_name], {self._input_name: user_history})[0]
        item_ids = tuple(int(item_id) for item_id in np.asarray(output).reshape(-1).tolist())
        return Recommendations(item_ids=item_ids)

