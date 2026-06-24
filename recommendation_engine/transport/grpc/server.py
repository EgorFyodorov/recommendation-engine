import logging
import os
import time
from concurrent import futures
from pathlib import Path

import grpc

from proto import recommender_pb2, recommender_pb2_grpc
from recommendation_engine.application import RecommendItems, ValidationError
from recommendation_engine.infrastructure import OnnxRecommendationEngine
from recommendation_engine.infrastructure.metrics import (
    MODEL_LOAD_DURATION_SECONDS,
    REQUEST_DURATION_SECONDS,
    REQUESTS_TOTAL,
    start_metrics_server,
)

DEFAULT_MODEL_PATH = Path("models/recommendation-engine.onnx")
DEFAULT_GRPC_PORT = 50051
DEFAULT_METRICS_PORT = 8000

logger = logging.getLogger(__name__)


class RecommenderGrpcService(recommender_pb2_grpc.RecommenderServicer):
    def __init__(self, use_case: RecommendItems) -> None:
        self._use_case = use_case

    def Recommend(self, request, context):
        started_at = time.perf_counter()
        item_count = len(request.item_ids)

        try:
            recommendations = self._use_case.execute(request.item_ids)
        except ValidationError as exc:
            duration_seconds = time.perf_counter() - started_at
            REQUESTS_TOTAL.labels(status="invalid_argument").inc()
            REQUEST_DURATION_SECONDS.observe(duration_seconds)
            logger.info(
                "recommendation request rejected item_count=%s duration_ms=%.2f error=%s",
                item_count,
                duration_seconds * 1000,
                exc,
            )
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception:
            duration_seconds = time.perf_counter() - started_at
            REQUESTS_TOTAL.labels(status="internal_error").inc()
            REQUEST_DURATION_SECONDS.observe(duration_seconds)
            logger.exception(
                "recommendation request failed item_count=%s duration_ms=%.2f",
                item_count,
                duration_seconds * 1000,
            )
            context.abort(grpc.StatusCode.INTERNAL, "internal recommendation error")

        duration_seconds = time.perf_counter() - started_at
        REQUESTS_TOTAL.labels(status="ok").inc()
        REQUEST_DURATION_SECONDS.observe(duration_seconds)
        logger.info(
            "recommendation request handled item_count=%s result_count=%s duration_ms=%.2f",
            item_count,
            len(recommendations),
            duration_seconds * 1000,
        )
        return recommender_pb2.RecommendResponse(item_ids=recommendations)


def create_grpc_server(use_case: RecommendItems, max_workers: int = 10) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    recommender_pb2_grpc.add_RecommenderServicer_to_server(
        RecommenderGrpcService(use_case),
        server,
    )
    return server


def build_use_case(model_path: str | Path) -> RecommendItems:
    engine = OnnxRecommendationEngine(model_path)
    return RecommendItems(engine)


def serve() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    model_path = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    port = int(os.getenv("GRPC_PORT", str(DEFAULT_GRPC_PORT)))
    metrics_port = int(os.getenv("METRICS_PORT", str(DEFAULT_METRICS_PORT)))

    model_load_started_at = time.perf_counter()
    use_case = build_use_case(model_path)
    MODEL_LOAD_DURATION_SECONDS.set(time.perf_counter() - model_load_started_at)

    start_metrics_server(metrics_port)
    logger.info("started Prometheus metrics endpoint on port=%s", metrics_port)

    server = create_grpc_server(use_case)
    bound_port = server.add_insecure_port(f"[::]:{port}")
    if bound_port == 0:
        raise RuntimeError(f"failed to bind gRPC server on port {port}")

    logger.info("starting gRPC recommender on port=%s model_path=%s", bound_port, model_path)
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("stopping gRPC recommender")
        server.stop(grace=5)


if __name__ == "__main__":
    serve()
