# Contributing

Thanks for helping improve Tower Upgrade Advisor. This app is small enough that good issues, focused pull requests, and verified data fixes are all useful.

## Local Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python app.py
```

## Checks

Run the same checks used for release readiness:

```bash
make lint
make typecheck
make test
make validate
make coverage-report
make stress
```

For public calculator coverage:

```bash
python scripts/verify_data_coverage.py --strict
```

## Data Changes

- Keep `data/upgrades.json` valid with `python -m src.data_loader validate`.
- Keep public coverage at 48/48 unless the public workshop calculator changes.
- Do not commit `data/raw/`, `data/profiles/`, local caches, or screenshots that are not used by docs.
- If refreshing from the public calculator, prefer `scripts/scrape_public_workshop_visible.py`.

## Pull Requests

1. Open an issue or clearly describe the bug/data/design problem.
2. Create a focused branch.
3. Include tests or verification output for behavior changes.
4. Update README/docs when user-facing behavior changes.
5. Keep unrelated formatting and generated files out of the PR.

