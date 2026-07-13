COMPOSE = docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.dev.yml

.PHONY: up down migrate backend frontend test gen-scene-schema gen-api-client verify-dev ollama-pull

up:
	@sh ./scripts/check_ports.sh
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec api uv run alembic upgrade head

backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm run lint

gen-scene-schema:
	@echo "TODO: implemented by task 2-1"

gen-api-client:
	@echo "TODO: implemented by API client generation task"

ollama-pull:
	$(COMPOSE) --profile gpu exec ollama ollama pull $${OLLAMA_MODEL_CHEAP}

verify-dev:
	$(MAKE) up
	@sh ./scripts/wait_for_health.sh
	$(MAKE) down
