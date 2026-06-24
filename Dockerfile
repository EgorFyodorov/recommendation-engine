FROM python:3.10-slim AS model-builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY modeling ./modeling

RUN uv sync --locked --extra modeling --no-dev
RUN uv run --locked python -m modeling.export_onnx --output /app/models/recommendation-engine.onnx
RUN uv run --locked python -m modeling.verify_onnx --model-path /app/models/recommendation-engine.onnx

FROM python:3.10-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.11 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV MODEL_PATH=/app/models/recommendation-engine.onnx
ENV GRPC_PORT=50051
ENV METRICS_PORT=8000

COPY pyproject.toml uv.lock README.md ./
COPY recommendation_engine ./recommendation_engine
COPY proto ./proto
COPY scripts ./scripts

RUN uv sync --locked --no-dev

COPY --from=model-builder /app/models ./models

EXPOSE 50051 8000

CMD ["uv", "run", "--locked", "python", "-m", "recommendation_engine.transport.grpc.server"]
