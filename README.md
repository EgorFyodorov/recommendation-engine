# Recommendation Engine

gRPC-сервис рекомендаций. Сервис принимает историю item ids,
запускает ONNX-модель через ONNX Runtime и возвращает top-k рекомендаций.

## Архитектура

Проект использует легкую луковую архитектуру:

- `recommendation_engine/domain` — доменные типы и порт рекомендательной модели.
- `recommendation_engine/application` — use case и валидация запроса.
- `recommendation_engine/infrastructure` — ONNX Runtime adapter.
- `recommendation_engine/transport/grpc` — gRPC server и transport mapping.
- `modeling` — PyTorch-модель, экспорт в ONNX и проверка эквивалентности.
- `proto` — gRPC контракт и сгенерированные Python bindings.

PyTorch-класс из ноутбука является source of truth для модели. ONNX-файл — generated
artifact. Runtime-сервис не использует PyTorch и загружает только ONNX-файл.

## Установка

```bash
uv sync --locked --extra dev --extra modeling
```

## Генерация protobuf bindings

```bash
uv run --locked --extra dev python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/recommender.proto
```

## Экспорт и проверка модели

```bash
make export
make verify
```

Экспорт создает `models/recommendation-engine.onnx`. Verifier прогоняет фиксированные истории
через PyTorch и ONNX Runtime и проверяет, что рекомендации совпадают.

Новый PyTorch ONNX exporter может сохранить веса отдельным файлом
`models/recommendation-engine.onnx.data`. В этом случае для запуска нужны оба файла:
`recommendation-engine.onnx` и `recommendation-engine.onnx.data`. Оба файла являются generated artifacts
и не коммитятся в репозиторий.

## Локальный запуск через Docker

```bash
make run
```

`make run` собирает Docker image, во время сборки экспортирует ONNX-модель, запускает
gRPC-сервис через Docker Compose и печатает логи в текущий терминал.

В другом терминале можно отправить запрос:

```bash
uv run --locked python scripts/client.py --items 1,2,3
```

То же самое через `make`:

```bash
make client
```

По умолчанию сервис слушает `localhost:50051`. Конфигурация:

- `MODEL_PATH=/app/models/recommendation-engine.onnx` внутри Docker image
- `GRPC_PORT=50051`
- `METRICS_PORT=8000`

Остановить foreground-запуск можно через `Ctrl+C`.

Если нужен detached-режим:

```bash
make run-detached
make logs
make stop
```

Для отладки без Docker можно запустить Python-сервис напрямую:

```bash
make export
make run-local
```

## Метрики

Сервис поднимает Prometheus endpoint на отдельном HTTP-порту:

```bash
curl http://localhost:8000/metrics
```

Через Makefile:

```bash
make metrics
```

Основные метрики:

- `recommendation_requests_total{status="ok|invalid_argument|internal_error"}`;
- `recommendation_request_duration_seconds`;
- `recommendation_model_load_duration_seconds`.

## Клиентский скрипт

Готовый клиент лежит в `scripts/client.py`. Он принимает историю пользователя через
CLI-параметр `--items`:

```bash
uv run --locked python scripts/client.py --items 1,2,3
```

Скрипт печатает рекомендованные item ids в stdout через запятую, например:

```text
8168,5614,1498,4748,4060,4710,4777,8245,6017,4359
```

## Docker

```bash
docker build -t recommendation-engine:local .
docker run --rm -p 50051:50051 -p 8000:8000 recommendation-engine:local
```

Или:

```bash
docker compose up --build
```

## Self-hosted deploy

Для деплоя на собственный сервер добавлен Ansible playbook:

```bash
deploy/ansible/deploy.yml
```

Пример inventory:

```bash
deploy/ansible/inventory.example.ini
```

Playbook ожидает сервер с уже установленными Docker и Docker Compose plugin.
Он проверяет их наличие, создает директорию приложения, рендерит
`docker-compose.yml`, делает `docker compose pull` и запускает сервис.

Минимальный ручной запуск:

```bash
uvx --from ansible-core ansible-playbook \
  -i deploy/ansible/inventory.example.ini \
  deploy/ansible/deploy.yml \
  -e "image=ghcr.io/OWNER/recommendation-engine:latest"
```

GitHub Actions CD workflow лежит в `.github/workflows/cd.yml`. Он собирает Docker
image, публикует его в GHCR и может запустить Ansible deploy.

Нужные GitHub secrets:

- `DEPLOY_HOST` — публичный host/IP сервера;
- `DEPLOY_USER` — SSH user;
- `DEPLOY_SSH_KEY` — private key для SSH;
- `DEPLOY_PORT` — SSH port, опционально.

Опциональные GitHub variables:

- `DEPLOY_APP_DIR`, по умолчанию `/opt/recommendation-engine`;
- `GRPC_PORT`, по умолчанию `50051`;
- `METRICS_PORT`, по умолчанию `8000`.

## Масштабирование и production hardening

Текущий вариант рассчитан на простой self-hosted deploy. Для production-сценария
gRPC-сервис лучше ставить за gateway/proxy, например Envoy, NGINX, Traefik, Kong
или cloud load balancer с поддержкой HTTP/2/gRPC.

Gateway/proxy должен отвечать за инфраструктурные concerns:

- TLS termination;
- rate limiting / RPS limiting;
- request size limits;
- access logs;
- retries/timeouts;
- load balancing между несколькими replicas сервиса.

В самом сервисе остаются application-level concerns:

- валидация входных `item_ids`;
- загрузка конкретной ONNX-модели;
- инференс через ONNX Runtime;
- бизнес-метрики и логи.

Для масштабирования можно запустить несколько одинаковых containers с одной и той же
версией ONNX-модели и балансировать gRPC-трафик через gateway. Так как модель
загружается при старте и запросы не требуют shared state, сервис горизонтально
масштабируется без дополнительной синхронизации.

Для управления версиями модели в production стоит вынести generated ONNX artifacts
из Docker build в model registry или object storage:

- хранить `model_name`, `model_version`, checksum и дату экспорта;
- деплоить сервис с явно заданным `MODEL_PATH`/model version;
- поддержать rollback на предыдущую модель;
- при необходимости проводить A/B test или canary rollout разных версий модели.

Prometheus endpoint `/metrics` уже добавлен. В production Prometheus должен scrape-ить
каждую replica сервиса, а алерты можно строить по error rate, latency histogram и
доступности metrics endpoint.

## gRPC API

```proto
service Recommender {
  rpc Recommend (RecommendRequest) returns (RecommendResponse);
}

message RecommendRequest {
  repeated int32 item_ids = 1;
}

message RecommendResponse {
  repeated int32 item_ids = 1;
}
```

Пустая история, отрицательные ids и ids больше либо равные `10000` возвращают
`INVALID_ARGUMENT`.

## Тесты и линтер

```bash
make lint
make test
```

Интеграционные ONNX-тесты автоматически пропускаются, если в окружении не установлены
`torch`, `onnx` и `onnxruntime`.
