from prometheus_client import Counter, Gauge, Histogram, start_http_server

REQUESTS_TOTAL = Counter(
    "recommendation_requests_total",
    "Total number of recommendation requests.",
    ("status",),
)

REQUEST_DURATION_SECONDS = Histogram(
    "recommendation_request_duration_seconds",
    "Recommendation request duration in seconds.",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

MODEL_LOAD_DURATION_SECONDS = Gauge(
    "recommendation_model_load_duration_seconds",
    "Duration of ONNX model loading during service startup.",
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)

