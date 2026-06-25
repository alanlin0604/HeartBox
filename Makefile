# HeartBox dev shortcuts.
#
# Works on Windows via gnumake (`choco install make`) or WSL.
# All targets assume the backend venv is at backend/venv/.

PY = backend/venv/Scripts/python.exe
PIP = backend/venv/Scripts/pip.exe

.PHONY: help test test-fast test-crisis test-llm-server test-django test-clean \
        load-kb runserver runserver-llm smoke check-env \
        pre-deploy lint deps-backend deps-llm gpu

help:
	@echo "HeartBox dev shortcuts:"
	@echo "  make test           - run full Django test suite (164+ tests, ~5 min)"
	@echo "  make test-fast      - crisis_guard + llm_server unit tests only (~10s)"
	@echo "  make test-crisis    - just crisis_guard (53 tests)"
	@echo "  make test-llm-server - just llm_server (21 tests)"
	@echo "  make test-django    - just Django backend (no crisis_guard / no llm_server)"
	@echo "  make test-clean     - full Django suite without --keepdb (CI parity, catches migration drift)"
	@echo ""
	@echo "  make runserver      - start Django dev server on :8000"
	@echo "  make runserver-llm  - start llm_server (FastAPI + TAIDE) on :8765"
	@echo "  make load-kb        - rebuild psychology_kb_bgem3 ChromaDB collection"
	@echo ""
	@echo "  make smoke          - end-to-end smoke test (health + chat + SSRF)"
	@echo "  make check-env      - verify torch/transformers/bnb/fastapi env"
	@echo ""
	@echo "  make pre-deploy     - run all pre-push checks (CI guard + tests)"
	@echo "  make lint           - ruff (if installed)"
	@echo "  make deps-backend   - pip install -r requirements.txt"
	@echo "  make deps-llm       - pip install -r requirements-llm.txt"
	@echo "  make gpu            - launch nvidia-smi GPU monitor"

test:
	cd backend && DISABLE_AI_PREWARM=1 venv/Scripts/python.exe manage.py test api --keepdb --noinput

test-fast: test-crisis test-llm-server

test-crisis:
	cd backend && DISABLE_AI_PREWARM=1 venv/Scripts/python.exe manage.py test api.test_crisis_guard --noinput

test-llm-server:
	$(PY) -m unittest discover -s llm_server.tests

test-django:
	cd backend && DISABLE_AI_PREWARM=1 venv/Scripts/python.exe manage.py test api.tests --keepdb --noinput

test-clean:
	cd backend && DISABLE_AI_PREWARM=1 venv/Scripts/python.exe manage.py test api --settings=moodnotes_pro.test_settings --noinput

runserver:
	cd backend && venv/Scripts/python.exe manage.py runserver 0.0.0.0:8000

runserver-llm:
	$(PY) -m llm_server --host 127.0.0.1 --port 8765

load-kb:
	cd backend && DISABLE_AI_PREWARM=1 venv/Scripts/python.exe manage.py load_knowledge_base --reset

smoke:
	powershell -ExecutionPolicy Bypass -File scripts/pre-deploy-check.ps1

check-env:
	$(PY) backend/check_env.py

pre-deploy:
	powershell -ExecutionPolicy Bypass -File scripts/pre-deploy-check.ps1

lint:
	-$(PY) -m ruff check backend llm_server

deps-backend:
	$(PIP) install -r requirements.txt

deps-llm:
	$(PIP) install -r requirements-llm.txt

gpu:
	powershell -ExecutionPolicy Bypass -File scripts/gpu-monitor.ps1
