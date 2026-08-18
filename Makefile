.PHONY: dev pipeline install check api state state-reset state-delete state-bootstrap test lint help

.DEFAULT_GOAL := help

dev: ## Levanta FastAPI + UI web en modo desarrollo
	./run.sh

pipeline: ## Ejecuta Fase 2 -> Fase 3 -> Fase 4 y levanta FastAPI + UI web
	./run.sh --with-pipeline

install: ## Crea .venv si falta e instala dependencias
	./run.sh --install --check

check: ## Verifica entorno, SQLite y dependencias sin levantar servidores
	./run.sh --check

api: ## Levanta sólo FastAPI, sin UI web
	./run.sh --api-only


state: ## Muestra output/pipeline_state.json
	.venv/bin/python tools/pipeline_state.py show

state-reset: ## Elimina el progreso y crea un estado limpio
	.venv/bin/python tools/pipeline_state.py reset

state-delete: ## Elimina el archivo de estado sin recrearlo
	.venv/bin/python tools/pipeline_state.py delete

state-bootstrap: ## Crea estado desde los outputs actuales de Fase 2, 3 y 4
	.venv/bin/python tools/pipeline_state.py bootstrap-current

test: ## Ejecuta pytest
	.venv/bin/python -m pytest -q

lint: ## Ejecuta Ruff
	.venv/bin/python -m ruff check .

help: ## Muestra comandos disponibles
	@/usr/bin/awk 'BEGIN {FS = ":.*##"; printf "Comandos disponibles:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  make %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
