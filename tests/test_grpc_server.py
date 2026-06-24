import grpc
import pytest

from proto import recommender_pb2, recommender_pb2_grpc
from recommendation_engine.application import ValidationError
from recommendation_engine.transport.grpc.server import create_grpc_server


class FakeUseCase:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.item_ids: tuple[int, ...] | None = None

    def execute(self, item_ids) -> list[int]:
        self.item_ids = tuple(item_ids)
        if self.error is not None:
            raise self.error
        return [7, 8, 9]


def test_grpc_server_returns_recommendations() -> None:
    use_case = FakeUseCase()
    server = create_grpc_server(use_case)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")

    try:
        grpc.channel_ready_future(channel).result(timeout=3)
        stub = recommender_pb2_grpc.RecommenderStub(channel)
        response = stub.Recommend(recommender_pb2.RecommendRequest(item_ids=[1, 2, 3]))
    finally:
        channel.close()
        server.stop(0)

    assert list(response.item_ids) == [7, 8, 9]
    assert use_case.item_ids == (1, 2, 3)


def test_grpc_server_maps_validation_error_to_invalid_argument() -> None:
    server = create_grpc_server(FakeUseCase(error=ValidationError("bad request")))
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")

    try:
        grpc.channel_ready_future(channel).result(timeout=3)
        stub = recommender_pb2_grpc.RecommenderStub(channel)
        with pytest.raises(grpc.RpcError) as exc_info:
            stub.Recommend(recommender_pb2.RecommendRequest(item_ids=[]))
    finally:
        channel.close()
        server.stop(0)

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
