.PHONY: bootstrap env-init dev dev-down format format-fix lint lint-sql typecheck test check generate-types db-push bootstrap-admin gate0

bootstrap:
	mkdir -p .uv-cache .bun-install/cache .bun-install/tmp
	cd api && UV_CACHE_DIR=../.uv-cache uv lock --check && UV_CACHE_DIR=../.uv-cache uv sync --locked
	cd web && BUN_INSTALL=$(CURDIR)/.bun-install BUN_INSTALL_CACHE_DIR=$(CURDIR)/.bun-install/cache TMPDIR=$(CURDIR)/.bun-install/tmp bun ci

env-init:
	test -f .env.local || (echo "ERROR: create .env.local first (see .env.example)"; exit 1)
	test -f web/.env.local || cp web/.env.example web/.env.local
	test -f api/.env || cp api/.env.example api/.env
	@echo "supabase CLI must be installed (brew install supabase/tap/supabase or npm i -g supabase)"

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-down:
	docker compose down

format:
	cd api && UV_CACHE_DIR=../.uv-cache uv run --locked ruff format --check .
	cd web && bun prettier --check src/

format-fix:
	cd api && UV_CACHE_DIR=../.uv-cache uv run --locked ruff format .
	cd web && bun prettier --write src/

lint:
	cd api && UV_CACHE_DIR=../.uv-cache uv run --locked ruff check .
	cd web && bun lint
	cd supabase/migrations && find . -name '*.sql' -exec echo "lint: {}" \;

lint-sql:
	@echo "SQL lint must be added via squawk or similar in CI"

typecheck:
	cd api && UV_CACHE_DIR=../.uv-cache uv run --locked mypy app/
	cd web && bun typecheck

test:
	cd api && UV_CACHE_DIR=../.uv-cache uv run --locked pytest -v
	cd web && bun test

generate-types:
	python3 scripts/generate_types.py
	bun scripts/generate_types.ts

db-push:
	@test -n "$(ENV)" || (echo "ERROR: ENV is required (local|staging|production)"; exit 1)
	@case "$(ENV)" in local) f=".env.local";; staging) f=".env.staging";; production) f=".env.production";; *) echo "Invalid ENV: $(ENV)"; exit 1;; esac; \
	test -f "$$f" || (echo "ERROR: $$f not found"; exit 1); \
	supabase db push --db-url "$$(grep '^SUPABASE_DB_URL=' "$$f" | cut -d= -f2-)"

bootstrap-admin:
	@test -n "$(EMAIL)" || (echo "ERROR: EMAIL is required"; exit 1)
	@test -n "$(ENV)" || (echo "ERROR: ENV is required"; exit 1)
	cd api && uv run --locked python ../scripts/bootstrap_admin.py --email "$(EMAIL)" --env "$(ENV)"

gate0:
	cd api && UV_CACHE_DIR=../.uv-cache uv run --locked python ../scripts/run_gate0.py

check: format lint typecheck test
