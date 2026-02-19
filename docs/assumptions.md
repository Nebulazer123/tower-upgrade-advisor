# Assumptions — Tower Upgrade Advisor

These assumptions were made by the team when the user did not specify preferences. Any of these can be overridden.

---

## Stack Assumptions

1. **Python 3.11+** is available on the development machine.
   - Rationale: Type hints, improved error messages, matched by .gitignore.

2. **Flask + htmx** is the UI stack (not Streamlit, Textual, or Electron).
   - Rationale: Best balance of control, stability, and daily-use UX.

3. **Pydantic v2** for data validation and models.
   - Rationale: Runtime type enforcement, JSON schema generation, widely adopted.

4. **pytest** for testing, **ruff** for linting/formatting, **mypy** for type checking.
   - Rationale: Modern Python standard tooling.

5. **uv** or **pip** for dependency management (no Poetry/PDM unless user prefers).
   - Rationale: Simplest setup; `pyproject.toml` for config.

---

## Data Assumptions

6. **The Tower game has approximately 25-35 permanent (coin-based) workshop upgrades.**
   - Exact count to be verified during data extraction.

7. **Upgrades are grouped into 3-4 categories: Attack, Defense, Utility, and possibly Special.**
   - Verified by reference site CSS: `.attack`, `.defense`, `.utility` classes found.

8. **Each upgrade has a maximum level that varies by upgrade** (some max at 50, others at 100+).
   - To be verified.

9. **Costs increase monotonically with level** (higher levels always cost more).
   - Standard for idle games; will be validated.

10. **Effects increase monotonically with level** (higher levels always give more benefit).
    - Standard for most upgrades; exceptions possible for special upgrades.

11. **Cost formulas may follow exponential or polynomial patterns** (e.g., `base * multiplier^level`).
    - We store raw per-level data, not formulas, as the source of truth.

12. **The reference site's data is accurate and reflects the current game version.**
    - If discrepancies are found, we document them and ask the user to verify.

---

## Scoring Assumptions

13. **"Marginal benefit per coin" is a reasonable V1 heuristic.**
    - It answers "what's the most efficient next spend?" which is the core use case.

14. **Cross-category comparison (damage vs health vs coins) is inherently approximate.**
    - We use user-configurable category weights as a pragmatic solution.

15. **Default category weights of 1.0 (attack, defense, utility) and 0.5 (special) are reasonable starting points.**
    - Users are expected to tune these.

16. **Special upgrades (Death Defy, Land Mines, Orb Speed) have lower default weight** because their value is more situational and harder to quantify.

17. **The tool recommends ONE upgrade per run** (not a budget plan for multiple upgrades).
    - Multi-step optimization is a future feature.

---

## UI/UX Assumptions

18. **Daily use on macOS via a web browser** (Chrome, Safari, Firefox).
    - The Flask server runs locally on `localhost:5000`.

19. **The user has 1-5 profiles** (different builds or accounts).
    - Profile storage is file-based; no database needed.

20. **The user knows their current upgrade levels** and can enter them manually.
    - No OCR, screenshot import, or API integration in V1.

21. **Upgrade ordering in the UI matches the in-game Workshop order.**
    - We use `display_order` from the data schema.

22. **The user wants to see transparent math** (not just "buy this").
    - Every recommendation shows the full formula, inputs, and alternatives.

---

## Technical Assumptions

23. **No authentication or multi-user support** needed (local tool for one person).

24. **No internet required after initial data extraction** (local-first).

25. **No database** — JSON files for data and profiles are sufficient for V1.

26. **The tool does not need to handle concurrent access** (single user, single browser tab).

27. **Port 5000 is available** on the user's machine for the Flask development server.

---

## Non-Assumptions (Things We Don't Assume)

- We do NOT assume the reference site's scoring logic is correct or discoverable
- We do NOT assume the game's formulas are publicly documented
- We do NOT assume the user wants a hosted/published tool
- We do NOT assume the user plays on any specific platform (iOS/Android)
- We do NOT assume the user wants in-run cash upgrade recommendations (explicitly out of scope)
