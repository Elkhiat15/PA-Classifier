# One command to run the demo: `make dev`
#
# It installs both toolchains, then runs the FastAPI backend and the Vite
# frontend together. Requires `poetry` and `npm` on PATH. The demo runs in mock
# mode with no API keys; set them in .env only for live classification.

.PHONY: help install install-backend install-frontend dev backend frontend \
        eval test-eval lint clean up up-d down logs

help:
	@echo "Targets:"
	@echo "  make install   - install backend (Poetry) + frontend (npm) deps"
	@echo "  make dev       - run backend (:8000) + frontend (:5173) together"
	@echo "  make backend   - run only the FastAPI server"
	@echo "  make frontend  - run only the Vite dev server"
	@echo "  make eval      - run the eval harness (pa-eval)"
	@echo "  make test-eval - run backend/evaluate.py (test set -> CSV)"
	@echo "  make lint      - ruff + mypy (backend)"
	@echo "  make clean     - remove build/test artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make up        - build + run via docker compose (http://localhost:8000)"
	@echo "  make up-d      - same, but detached (background)"
	@echo "  make down      - stop the docker compose stack"
	@echo "  make logs      - follow logs of the detached stack (Ctrl-C to exit)"

install: install-backend install-frontend

install-backend:
	poetry install

install-frontend:
	cd frontend && npm install

# Run both servers. Ctrl-C stops both. The frontend proxies /api to the backend.
dev:
	@echo "Backend  -> http://127.0.0.1:8000  (docs at /docs)"
	@echo "Frontend -> http://localhost:5173"
	@( cd backend && poetry run pa-serve & \
	   cd frontend && npm run dev & \
	   wait )

backend:
	cd backend && poetry run pa-serve

frontend:
	cd frontend && npm run dev

# ---- Docker ---------------------------------------------------------------

# Build the image and run the app in the foreground. Ctrl-C stops it.
# The frontend and API are both served at http://localhost:8000
up:
	docker compose up --build

# Same, but detached (runs in the background).
up-d:
	docker compose up --build -d

# Stop and remove the containers (and their network).
down:
	docker compose down

# Follow logs of the running (detached) container. Ctrl-C exits.
logs:
	docker compose logs -f

eval:
	poetry run pa-eval --data eval/data/cases_v1.jsonl --out eval/results/latest

# Run the standalone evaluation script (backend/evaluate.py) over the test
# dataset; streams predictions to eval/data/test_results.csv.
test-eval:
	cd backend && poetry run python evaluate.py

lint:
	poetry run ruff check .
	poetry run mypy src

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache eval/results
	rm -rf frontend/dist frontend/node_modules/.vite