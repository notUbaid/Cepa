.PHONY: help install install-dev test test-cov lint run clean

help:
	@echo "CEPA Mandi Quality Assaying Engine"
	@echo "-----------------------------------"
	@echo "make install      Install production dependencies"
	@echo "make install-dev  Install development & testing dependencies"
	@echo "make test         Run automated test suite (pytest -q)"
	@echo "make test-cov     Run tests with coverage report"
	@echo "make run          Launch backend server (localhost:8000)"
	@echo "make clean        Remove cache and build artifacts"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest -q

test-cov:
	pytest -v --cov=backend --cov-report=term-missing

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.cache" -delete
	rm -rf .pytest_cache .coverage htmlcov
