# Cursor Runbook — Tower Upgrade Advisor

> **Purpose:** How to use Cursor IDE effectively for this project.

---

## Getting Started with Cursor

### 1. Install Cursor
- Download from https://cursor.com
- Install and open.

### 2. Open the Project
- File → Open Folder → select the `tower-upgrade-advisor` directory.
- Cursor will detect `pyproject.toml` and offer to set up a Python environment.

### 3. Set Up Context

Cursor works best when it understands your project. Feed it context:

**Recommended files to add to Cursor's context (drag into chat or use @-mention):**
1. `docs/transfer_pack.md` — project overview and current status
2. `docs/game_and_project_context.md` — game mechanics and requirements
3. `docs/todo_now.md` — what to work on next
4. `docs/extraction_playbook.md` — if working on data extraction

### 4. First Message

Paste the contents of `prompts/cursor_kickoff.md` as your first message in a new Cursor chat session. This gives the agent full project context in one shot.

---

## Project-Specific Cursor Tips

### Use the terminal
Cursor has an integrated terminal. Use it for:
```bash
# Run tests after changes
pytest -x -q

# Lint after changes
ruff check src/ tests/ scripts/

# Full check
make check
```

### Context window management
This project has many docs. Don't dump everything at once. Use this priority:
1. **Always include:** `docs/transfer_pack.md`, `docs/todo_now.md`
2. **For data work:** add `docs/extraction_playbook.md`, `scripts/extract_data.py`
3. **For model changes:** add `src/models.py`, `docs/data_schema.md`
4. **For scoring changes:** add `src/scoring.py`, `docs/scoring.md`
5. **For UI work:** add `docs/plan_ui.md`, `docs/plan_architect.md`

### Ask Cursor to verify
After any code change, ask Cursor to:
1. Run `pytest -x -q`
2. Run `ruff check src/ tests/ scripts/`
3. Check that the change is consistent with `docs/decisions.md`

---

## Key Files for Cursor

| File | When to Reference |
|------|-------------------|
| `src/models.py` | Any data model question |
| `src/scoring.py` | Scoring algorithm changes |
| `src/data_loader.py` | Data loading/validation |
| `src/profile_manager.py` | Profile CRUD |
| `scripts/extract_data.py` | Data extraction |
| `tests/conftest.py` | Understanding test fixtures |
| `tests/fixtures/test_upgrades.json` | Test data format |
| `docs/game_and_project_context.md` | Game mechanics questions |
| `docs/decisions.md` | Why something was built a certain way |
| `docs/assumptions.md` | What was assumed vs. verified |

---

## Common Cursor Workflows

### "Fix a test failure"
1. Share the test file and the source file it tests.
2. Share the error output.
3. Ask Cursor to fix and re-run.

### "Add a new feature"
1. Share `docs/todo_now.md` to show what's prioritized.
2. Share the relevant source files.
3. Ask Cursor to implement with tests.
4. Verify: `pytest -x -q && ruff check src/ tests/ scripts/`

### "Run data extraction"
1. Share `docs/extraction_playbook.md` and `scripts/extract_data.py`.
2. Ask Cursor to run the extraction and debug any failures.
3. After success: `python -m src.data_loader validate`

### "Build the Flask UI"
1. Share `docs/plan_ui.md` and `docs/plan_architect.md`.
2. Share `src/models.py` and `src/scoring.py` for the data layer.
3. Ask Cursor to create `app.py`, templates, and routes.
