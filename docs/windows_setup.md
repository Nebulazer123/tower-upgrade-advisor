# Windows Setup — Tower Upgrade Advisor

> **Purpose:** Get the project running on Windows from scratch.

---

## Prerequisites

### 1. Python 3.11+

**Option A — Official installer (recommended):**
1. Download from https://www.python.org/downloads/
2. During install, check "Add Python to PATH".
3. Verify: `python --version` should show 3.11+.

**Option B — Via winget:**
```powershell
winget install Python.Python.3.11
```

**Option C — Via Chocolatey:**
```powershell
choco install python311
```

### 2. Git

```powershell
# Check if installed
git --version

# Install if needed
winget install Git.Git
```

**Important:** Configure line endings:
```bash
git config --global core.autocrlf true
```

### 3. Make (Optional)

The `Makefile` uses GNU Make. On Windows you can either:
- Install Make: `choco install make`
- Or run the underlying commands directly (documented below)

---

## Setup Steps

```powershell
# 1. Clone the repo
git clone https://github.com/Nebulazer123/tower-upgrade-advisor.git
cd tower-upgrade-advisor

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies (dev mode)
pip install -e ".[dev]"

# 4. Verify tests pass
pytest -x -q
# Expected: 67 passed

# 5. Verify lint is clean
ruff check src/ tests/ scripts/
# Expected: All checks passed!
```

---

## Extraction Dependencies (Phase 4)

When you're ready to run data extraction:

```powershell
# Install extraction deps
pip install -e ".[extract]"

# Install Chromium for Playwright
playwright install chromium

# Run extraction
python scripts/extract_data.py
```

---

## Commands Without Make

If you don't install Make, here are the equivalent commands:

| Make target | Direct command |
|-------------|---------------|
| `make install` | `pip install -e .` |
| `make install-dev` | `pip install -e ".[dev]"` |
| `make install-extract` | `pip install -e ".[extract]" && playwright install chromium` |
| `make test` | `pytest -x -q` |
| `make test-cov` | `pytest --cov=src --cov-report=term-missing` |
| `make lint` | `ruff check src/ tests/ && ruff format --check src/ tests/` |
| `make lint-fix` | `ruff check --fix src/ tests/ && ruff format src/ tests/` |
| `make typecheck` | `mypy src/` |
| `make validate` | `python -m src.data_loader validate` |

---

## Troubleshooting

### "python is not recognized"
- Ensure Python is in your PATH. Re-run the installer and check "Add Python to PATH."
- Try `python3` instead of `python`.

### "pip install fails with permission error"
- Use a virtual environment (see setup steps above).
- Or use `pip install --user -e ".[dev]"`.

### "playwright install fails"
- Ensure you're in the virtual environment.
- Try: `python -m playwright install chromium`

### "ruff/pytest not found"
- Ensure you installed dev dependencies: `pip install -e ".[dev]"`
- Ensure your virtual environment is activated.

### Line ending issues (CRLF vs LF)
```bash
git config --global core.autocrlf true
```
