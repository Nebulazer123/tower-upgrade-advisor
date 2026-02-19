# Migration Checklist — Tower Upgrade Advisor

> **Purpose:** Step-by-step checklist for setting up the project on a new machine, in a new IDE, or on a new OS.

---

## Scenario A: macOS → Windows (same repo)

- [ ] Clone the repo: `git clone https://github.com/Nebulazer123/tower-upgrade-advisor.git`
- [ ] Follow `docs/windows_setup.md` for Windows-specific setup
- [ ] Run `pytest -x -q` — all 67 tests must pass
- [ ] Run `ruff check src/ tests/ scripts/` — must be clean
- [ ] Read `docs/todo_now.md` to know what's next

## Scenario B: VS Code Copilot → Cursor (same machine)

- [ ] Install Cursor from https://cursor.com
- [ ] Open the project folder in Cursor
- [ ] Follow `docs/cursor_runbook.md` for Cursor-specific setup
- [ ] Paste `prompts/cursor_kickoff.md` as first message in Cursor chat
- [ ] Verify tests pass: `pytest -x -q`

## Scenario C: Fresh clone on any machine

- [ ] `git clone https://github.com/Nebulazer123/tower-upgrade-advisor.git`
- [ ] `cd tower-upgrade-advisor`
- [ ] Follow the OS-specific setup guide:
  - macOS: `docs/macos_setup.md`
  - Windows: `docs/windows_setup.md`
- [ ] `pip install -e ".[dev]"`
- [ ] `pytest -x -q` (67 tests must pass)
- [ ] `ruff check src/ tests/ scripts/` (must be clean)
- [ ] Read `docs/transfer_pack.md` for project overview
- [ ] Read `docs/todo_now.md` for next steps

---

## Critical Files to Verify After Migration

| File | Must Exist | Purpose |
|------|-----------|---------|
| `pyproject.toml` | Yes | Project config, dependencies |
| `Makefile` | Yes | Dev workflow commands |
| `src/models.py` | Yes | Core data models |
| `src/scoring.py` | Yes | Scoring engines |
| `src/data_loader.py` | Yes | Data loading + validation |
| `src/profile_manager.py` | Yes | Profile CRUD |
| `scripts/extract_data.py` | Yes | Data extraction script |
| `tests/conftest.py` | Yes | Test fixtures |
| `tests/fixtures/test_upgrades.json` | Yes | Test data |
| `data/upgrades.json` | No (Phase 4) | Real data — not yet extracted |
| `data/raw/` | No (runtime) | Raw extraction artifacts |

---

## Known Platform Differences

| Item | macOS | Windows |
|------|-------|---------|
| Python command | `python3` | `python` (usually) |
| Playwright browsers | `~/.cache/ms-playwright/` | `%LOCALAPPDATA%\ms-playwright\` |
| File paths | `/Users/...` | `C:\Users\...` |
| Line endings | LF | CRLF (configure git: `core.autocrlf=true`) |
| Make | Pre-installed | Install via `choco install make` or use commands directly |
