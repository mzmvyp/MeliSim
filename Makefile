# MeliSim — developer shortcuts.
#
# Use `make <target>`. On Windows, run from git-bash or WSL so `sh`-style
# scripts (docker compose, bash) work.

.PHONY: help up up-bg down build logs ps test smoke lint clean \
        obs-open grafana prometheus jaeger

SHELL := /bin/bash

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	 | awk 'BEGIN{FS=":.*?## "};{printf "\033[36m%-18s\033[0m %s\n",$$1,$$2}'

up: build up-bg  ## Build images and start the whole stack in background
up-bg:  ## Start all services in background (assumes images built)
	docker compose up -d
	@echo ""
	@echo "  Gateway:     http://localhost:8000/docs"
	@echo "  Grafana:     http://localhost:3000    (anonymous, dashboard: MeliSim overview)"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  Jaeger:      http://localhost:16686"
	@echo ""

down:  ## Stop stack and remove containers + volumes
	docker compose down -v

build:  ## Build all service images
	docker compose build

logs:  ## Tail logs of every service
	docker compose logs -f --tail=50

ps:  ## Show container status
	docker compose ps

smoke:  ## End-to-end smoke test (requires stack running)
	./test.sh

test:  ## Run unit tests for every service (local toolchains required)
	@echo "─── python services ───"
	@for s in api-gateway payments-service notifications-service search-service; do \
	  echo "  $$s"; (cd $$s && pytest -q) || exit 1; \
	done
	@echo "─── users-service (Maven) ───"
	@cd users-service && mvn -B -q test
	@echo "─── orders-service (Gradle) ───"
	@cd orders-service && ./gradlew test --no-daemon
	@echo "─── go services ───"
	@for s in products-service stock-monitor; do \
	  echo "  $$s"; (cd $$s && go mod tidy && go test ./...) || exit 1; \
	done

lint:  ## Run linters in every language (best-effort, skip if tool missing)
	@command -v ruff >/dev/null && ruff check api-gateway payments-service notifications-service search-service || echo "skip ruff"
	@command -v golangci-lint >/dev/null && (cd products-service && golangci-lint run ./...) || echo "skip golangci-lint"

clean: down  ## Stop everything and prune dangling images
	docker image prune -f

obs-open:  ## Open Grafana, Prometheus and Jaeger (Linux/WSL: xdg-open; mac: open)
	@command -v xdg-open >/dev/null && { xdg-open http://localhost:3000; xdg-open http://localhost:9090; xdg-open http://localhost:16686; } \
	 || { open http://localhost:3000 2>/dev/null; open http://localhost:9090 2>/dev/null; open http://localhost:16686 2>/dev/null; } \
	 || echo "please open: http://localhost:3000 | :9090 | :16686"
