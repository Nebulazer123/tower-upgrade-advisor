.PHONY: test test-all lint typecheck check validate coverage-report verify-site scrape-visible stress run install install-dev install-extract

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
	ruff check src/ tests/ app.py scripts/verify_data_coverage.py scripts/verify_site_structure.py scripts/scrape_public_workshop_visible.py scripts/stress_test_app.py
	ruff format --check src/ tests/ app.py scripts/verify_data_coverage.py scripts/verify_site_structure.py scripts/scrape_public_workshop_visible.py scripts/stress_test_app.py

lint-fix:
	ruff check --fix src/ tests/ app.py scripts/verify_data_coverage.py scripts/verify_site_structure.py scripts/scrape_public_workshop_visible.py scripts/stress_test_app.py
	ruff format src/ tests/ app.py scripts/verify_data_coverage.py scripts/verify_site_structure.py scripts/scrape_public_workshop_visible.py scripts/stress_test_app.py

typecheck:
	mypy src/ app.py

validate:
	python -m src.data_loader validate

coverage-report:
	python scripts/verify_data_coverage.py

verify-site:
	python scripts/verify_site_structure.py

scrape-visible:
	python scripts/scrape_public_workshop_visible.py

stress:
	python scripts/stress_test_app.py

check: lint test validate

run:
	python app.py
