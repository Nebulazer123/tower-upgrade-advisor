.PHONY: test test-all lint typecheck check validate run install install-dev install-extract

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-extract:
	pip install -e ".[extract]"
	playwright install chromium

test:
	pytest -x -q

test-all:
	pytest -x -q -m ""

test-cov:
	pytest --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

lint-fix:
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck:
	mypy src/

validate:
	python -m src.data_loader validate

check: lint test validate

run:
	python app.py
