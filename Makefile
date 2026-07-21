.PHONY: backend frontend dev install help paper paper-clean

help:
	@echo "make backend   - run the FastAPI backend on http://localhost:8080"
	@echo "make frontend  - run the Svelte frontend on http://localhost:5173"
	@echo "make dev       - run backend + frontend together"
	@echo "make install   - install backend (uv) and frontend (npm) deps"
	@echo "make paper       - build the thesis (paper/main.tex -> paper/paper.pdf)"
	@echo "make paper-clean - remove the thesis LaTeX aux files"

backend:
	uv run --extra backend uvicorn backend.app:app --reload --port 8080

frontend:
	cd frontend && npm run dev

dev:
	@$(MAKE) -j2 backend frontend

install:
	uv sync --extra backend --extra dev
	cd frontend && npm install

paper:
	$(MAKE) -C paper

paper-clean:
	$(MAKE) -C paper clean
