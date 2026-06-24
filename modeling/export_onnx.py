import argparse
from pathlib import Path

import torch

from modeling.model import DEFAULT_NUM_RECOMMENDATIONS, Model

DEFAULT_OPSET_VERSION = 18
DEFAULT_DUMMY_HISTORY = (1, 42, 100)
DEFAULT_EXPORT_SEED = 42


def export_onnx(
    output_path: str | Path,
    num_recommendations: int = DEFAULT_NUM_RECOMMENDATIONS,
    seed: int = DEFAULT_EXPORT_SEED,
    opset_version: int = DEFAULT_OPSET_VERSION,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(seed)
    model = Model(num_recommendations=num_recommendations)
    model.eval()

    dummy_history = torch.tensor(DEFAULT_DUMMY_HISTORY, dtype=torch.long)

    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_history,
            str(output_path),
            input_names=["user_history"],
            output_names=["recommendations"],
            dynamic_axes={"user_history": {0: "history_len"}},
            opset_version=opset_version,
            do_constant_folding=True,
        )

    import onnx

    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the PyTorch recommender to ONNX.")
    parser.add_argument("--output", type=Path, default=Path("models/recommendation-engine.onnx"))
    parser.add_argument("--num-recommendations", type=int, default=DEFAULT_NUM_RECOMMENDATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_EXPORT_SEED)
    parser.add_argument("--opset-version", type=int, default=DEFAULT_OPSET_VERSION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_onnx(
        output_path=args.output,
        num_recommendations=args.num_recommendations,
        seed=args.seed,
        opset_version=args.opset_version,
    )
    print(f"Exported ONNX model to {output_path}")


if __name__ == "__main__":
    main()
