.PHONY: help install install-dev test test-cov lint run clean demo-preflight eval-real attack-tests

help:
	@echo "CEPA Mandi Quality Assaying Engine"
	@echo "-----------------------------------"
	@echo "make install         Install production dependencies"
	@echo "make install-dev     Install development & testing dependencies"
	@echo "make test            Run automated test suite (pytest -q)"
	@echo "make test-cov        Run tests with coverage report"
	@echo "make attack-tests    Run 20-vector judge attack test suite"
	@echo "make preflight       Run automated system preflight audit"
	@echo "make demo            Launch FastAPI demo server"
	@echo "make eval-real       Run real PyTorch evaluation pipeline"
	@echo "make run             Launch backend server (localhost:8000)"
	@echo "make clean           Remove cache and build artifacts"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest -q

test-cov:
	pytest -v --cov=backend --cov-report=term-missing

attack-tests:
	pytest -v backend/tests/test_judge_attack.py

preflight:
	python backend/scripts/preflight.py

demo:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

demo-preflight:
	python backend/scripts/preflight.py

eval-real:
	python ml/evaluate_real.py

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.cache" -delete
	rm -rf .pytest_cache .coverage htmlcov
