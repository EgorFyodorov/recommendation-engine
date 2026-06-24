# Recommendation Engine

gRPC-сервис рекомендаций. Сервис принимает историю item ids, запускает
ONNX-модель через ONNX Runtime и возвращает top-k рекомендаций.

## Быстрая проверка

### Локально через Docker

```bash
make run
```

`make run` собирает Docker image, во время сборки экспортирует ONNX-модель,
запускает gRPC-сервис через Docker Compose и печатает логи в текущий терминал.

В другом терминале:

```bash
uv run --locked python scripts/client.py --items 1,2,3
```

То же самое через Makefile:

```bash
make client
```

Остановить foreground-запуск можно через `Ctrl+C`.

Detached-режим:

```bash
make run-detached
make logs
make stop
```

### Публичный endpoint

```bash
uv run --locked python scripts/client.py --address 185.141.227.197:50051 --items 1,2,3
```

Клиент печатает `RecommendResponse` в JSON-формате:

```json
{"item_ids": [8168, 5614, 1498, 4748, 4060, 4710, 4777, 8245, 6017, 4359]}
```

### Метрики

Prometheus endpoint доступен на отдельном HTTP-порту:

```bash
curl http://localhost:8000/metrics
curl http://185.141.227.197:8000/metrics
```

Основные метрики:

- `recommendation_requests_total{status="ok|invalid_argument|internal_error"}`;
- `recommendation_request_duration_seconds`;
- `recommendation_model_load_duration_seconds`.

## Модель и ONNX

PyTorch-класс из ноутбука является source of truth для модели. ONNX-файл —
generated artifact. Runtime-сервис не использует PyTorch и загружает только
ONNX-модель через ONNX Runtime.

Экспорт и проверка:

```bash
make export
make verify
```

Экспорт создает `models/recommendation-engine.onnx`. Новый PyTorch ONNX exporter
может сохранить веса отдельным файлом `models/recommendation-engine.onnx.data`.
В этом случае для запуска нужны оба файла. Они являются generated artifacts и не
коммитятся в репозиторий.

Verifier прогоняет фиксированные истории через PyTorch и ONNX Runtime и проверяет,
что рекомендации совпадают.

## Архитектура

Проект использует легкую луковую архитектуру:

- `recommendation_engine/domain` — доменные типы и порт рекомендательной модели;
- `recommendation_engine/application` — use case и валидация запроса;
- `recommendation_engine/infrastructure` — ONNX Runtime adapter и метрики;
- `recommendation_engine/transport/grpc` — gRPC server и transport mapping;
- `modeling` — PyTorch-модель, экспорт в ONNX и проверка эквивалентности;
- `proto` — gRPC контракт и сгенерированные Python bindings.

## gRPC API

Контракт сервиса описан в `proto/recommender.proto`. Python bindings
`proto/recommender_pb2.py` и `proto/recommender_pb2_grpc.py` уже сгенерированы и
закоммичены. Для обычного запуска ничего генерировать не нужно.

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

Если контракт меняется, bindings можно пересобрать:

```bash
make proto
```

## Разработка

Установка зависимостей:

```bash
uv sync --locked --extra dev --extra modeling
```

Проверки:

```bash
make lint
make test
```

Запуск без Docker для отладки:

```bash
make export
make run-local
```

Низкоуровневые Docker-команды:

```bash
docker build -t recommendation-engine:local .
docker run --rm -p 50051:50051 -p 8000:8000 recommendation-engine:local
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

Playbook ожидает сервер с уже установленными Docker и Docker Compose plugin. Он
проверяет их наличие, создает директорию приложения, рендерит `docker-compose.yml`,
делает `docker compose pull` и запускает сервис.

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

CI запускается на `push` и `pull_request` для любых веток. CD собирает и публикует
Docker image на push в `main`; deploy на сервер запускается вручную через
`workflow_dispatch`.

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
