import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from modeling.model import Model

DEFAULT_HISTORIES = (
    (1, 2, 3),
    (0,),
    (9999, 7, 42, 42),
)
DEFAULT_EXPORT_SEED = 42


@dataclass(frozen=True)
class VerificationResult:
    history: tuple[int, ...]
    pytorch_output: tuple[int, ...]
    onnx_output: tuple[int, ...]


def verify_onnx(
    model_path: str | Path,
    histories: Iterable[tuple[int, ...]] = DEFAULT_HISTORIES,
    seed: int = DEFAULT_EXPORT_SEED,
) -> list[VerificationResult]:
    import onnxruntime as ort

    model_path = Path(model_path)
    torch.manual_seed(seed)
    pytorch_model = Model()
    pytorch_model.eval()
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])

    results: list[VerificationResult] = []
    for history in histories:
        pytorch_input = torch.tensor(history, dtype=torch.long)
        onnx_input = np.asarray(history, dtype=np.int64)

        with torch.no_grad():
            pytorch_output = pytorch_model(pytorch_input).detach().cpu().numpy()
        onnx_output = session.run(["recommendations"], {"user_history": onnx_input})[0]

        pytorch_ids = tuple(int(item_id) for item_id in pytorch_output.reshape(-1).tolist())
        onnx_ids = tuple(int(item_id) for item_id in onnx_output.reshape(-1).tolist())
        result = VerificationResult(
            history=tuple(history),
            pytorch_output=pytorch_ids,
            onnx_output=onnx_ids,
        )
        if result.pytorch_output != result.onnx_output:
            raise AssertionError(
                "ONNX output differs from PyTorch output "
                f"for history={result.history}: "
                f"pytorch={result.pytorch_output}, onnx={result.onnx_output}"
            )
        results.append(result)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify that ONNX output matches PyTorch output.")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("models/recommendation-engine.onnx"),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_EXPORT_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = verify_onnx(model_path=args.model_path, seed=args.seed)
    for result in results:
        print(f"OK history={result.history} recommendations={result.onnx_output}")


if __name__ == "__main__":
    main()
