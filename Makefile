UV ?= uv
MODEL_PATH ?= models/recommendation-engine.onnx
GRPC_PORT ?= 50051
METRICS_PORT ?= 8000

.PHONY: install install-dev proto export verify test lint run run-detached run-local logs stop client metrics docker-build docker-run

install:
	$(UV) sync --locked --no-dev

install-dev:
	$(UV) sync --locked --extra dev --extra modeling

proto:
	$(UV) run --locked --extra dev python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/recommender.proto

export:
	$(UV) run --locked --extra modeling python -m modeling.export_onnx --output $(MODEL_PATH)

verify:
	$(UV) run --locked --extra modeling python -m modeling.verify_onnx --model-path $(MODEL_PATH)

test:
	$(UV) run --locked --extra dev --extra modeling pytest

lint:
	$(UV) run --locked --extra dev ruff check .

run:
	docker compose up --build

run-detached:
	docker compose up --build -d

run-local:
	MODEL_PATH=$(MODEL_PATH) GRPC_PORT=$(GRPC_PORT) METRICS_PORT=$(METRICS_PORT) $(UV) run --locked python -m recommendation_engine.transport.grpc.server

logs:
	docker compose logs -f recommendation-engine

stop:
	docker compose down

client:
	$(UV) run --locked python scripts/client.py --items 1,2,3

metrics:
	curl -s http://localhost:$(METRICS_PORT)/metrics

docker-build:
	docker build -t recommendation-engine:local .

docker-run:
	docker run --rm -p 50051:50051 -p 8000:8000 recommendation-engine:local
