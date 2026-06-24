import argparse

import grpc

from proto import recommender_pb2, recommender_pb2_grpc


def parse_items(raw_items: str) -> list[int]:
    if not raw_items:
        return []
    return [int(item_id.strip()) for item_id in raw_items.split(",") if item_id.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call the recommender gRPC service.")
    parser.add_argument("--address", default="localhost:50051")
    parser.add_argument("--items", required=True, help="Comma-separated item ids, e.g. 1,2,3")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    item_ids = parse_items(args.items)

    with grpc.insecure_channel(args.address) as channel:
        stub = recommender_pb2_grpc.RecommenderStub(channel)
        response = stub.Recommend(recommender_pb2.RecommendRequest(item_ids=item_ids))

    print(",".join(str(item_id) for item_id in response.item_ids))


if __name__ == "__main__":
    main()

