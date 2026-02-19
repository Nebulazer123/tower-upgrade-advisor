# Cursor Kickoff Prompt — Tower Upgrade Advisor

> **How to use:** Copy everything below the line and paste it as your first message in a new Cursor chat session.

---

## Context: Tower Upgrade Advisor

You are resuming work on the **Tower Upgrade Advisor** project. This is a local-first Python tool that recommends the best next permanent upgrade to buy in the mobile game "The Tower" (idle tower defense).

### Project status
- **Phase 1 (Planning):** Complete. 13 docs in `docs/`.
- **Phase 2 (Foundation):** Complete. Models, scoring, data loader, profile manager. 67 tests, lint clean.
- **Phase 3 (Transfer Pack):** Complete. Migration docs, extraction playbook, this prompt.
- **Phase 4 (Data Extraction):** NOT STARTED. This is the critical next step.
- **Phase 5 (Flask UI):** NOT STARTED.

### Stack
Python 3.11+, Flask + htmx, Pydantic v2, pytest, ruff.

### Key files to read first
1. `docs/transfer_pack.md` — full project overview, repo layout, golden commands
2. `docs/todo_now.md` — prioritized task list (start here for what to do)
3. `docs/game_and_project_context.md` — game mechanics and project requirements (384 lines, authoritative)
4. `docs/extraction_playbook.md` — step-by-step data extraction guide
5. `docs/decisions.md` — 9 documented decisions with rationale

### Verify the repo is healthy
```bash
pytest -x -q                         # expect 67 passed
ruff check src/ tests/ scripts/      # expect clean
```

### What to do next
Read `docs/todo_now.md`. The #1 priority is **data extraction**:
1. Run `pip install -e ".[extract]" && playwright install chromium`
2. Run `python scripts/extract_data.py`
3. Debug failures using `docs/extraction_playbook.md`
4. Validate with `python -m src.data_loader validate`
5. Update category Literal in `src/models.py` to match extracted data

### Rules
- **Never invent data.** If extraction fails, debug it or use manual fallback. Do not make up costs, effects, or levels.
- **Never add hidden weights.** Scoring must be transparent and user-controllable.
- **Always run tests after changes.** `pytest -x -q` must pass.
- **Always run lint after changes.** `ruff check src/ tests/ scripts/` must be clean.
- **Document decisions** in `docs/decisions.md` with rationale.
- **Document assumptions** in `docs/assumptions.md`.
- **Log research** in `docs/research_notes.md` using the template.

### Known issue: category names
The code currently has `Literal["offense", "defense", "economy", "utility"]` but the user confirmed categories are **attack, defense, utility**. This must be updated after extraction reveals the actual data format.

### Game categories (from user)
- **Attack:** damage, attack speed, critical chance, critical factor, etc.
- **Defense:** health, health regen, defense, thorns, etc.
- **Utility:** coins per kill, coins per wave, interest, land mines, death defy, orb speed, etc.

### Scoring approach
Two modes, no hardcoded weights:
1. **Per-category best:** `score = marginal_benefit / cost` within each category independently
2. **Balanced mode:** `score = marginal_benefit / cost * slider_weight(category)` with 3 user-adjustable sliders (default 1.0)

Please read the key files listed above and then proceed with the first priority in `docs/todo_now.md`.
