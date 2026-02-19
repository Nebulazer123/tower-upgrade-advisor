# macOS Setup — Tower Upgrade Advisor

> **Purpose:** Get the project running on macOS from scratch.

---

## Prerequisites

### 1. Python 3.11+

**Option A — Homebrew (recommended):**
```bash
brew install python@3.11
```

**Option B — Official installer:**
Download from https://www.python.org/downloads/

**Verify:**
```bash
python3 --version
# Should show 3.11+
```

> **Note:** On macOS, use `python3` and `pip3` (not `python`/`pip`) unless you've aliased them.

### 2. Git

```bash
# Usually pre-installed on macOS. Verify:
git --version

# Install via Homebrew if needed:
brew install git
```

### 3. Make

Pre-installed on macOS (via Xcode Command Line Tools).

```bash
# If not available:
xcode-select --install
```

---

## Setup Steps

```bash
# 1. Clone the repo
git clone https://github.com/Nebulazer123/tower-upgrade-advisor.git
cd tower-upgrade-advisor

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

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

```bash
# Install extraction deps
pip install -e ".[extract]"

# Install Chromium for Playwright
playwright install chromium

# Run extraction
python3 scripts/extract_data.py
```

---

## Quick Reference (Make targets)

```bash
make install         # Install runtime deps
make install-dev     # Install dev deps (pytest, ruff, mypy)
make install-extract # Install extraction deps (playwright, httpx)
make test            # Run tests (pytest -x -q)
make test-cov        # Run tests with coverage
make lint            # Check lint (ruff)
make lint-fix        # Auto-fix lint issues
make typecheck       # Run mypy
make validate        # Validate data/upgrades.json
make check           # lint + test + validate
```

---

## Troubleshooting

### "`python` not found" but `python3` works
This is normal on macOS. Use `python3` explicitly, or create an alias:
```bash
alias python=python3
alias pip=pip3
```

### "pip install fails outside venv"
Always use a virtual environment. System Python on macOS is managed by the OS.

### "playwright install hangs or fails"
```bash
# Ensure you're in the venv
source .venv/bin/activate
python3 -m playwright install chromium
```

### "Port 5000 in use" (when Flask UI is built)
macOS Monterey+ uses port 5000 for AirPlay. Either:
- Disable AirPlay Receiver in System Preferences → Sharing
- Or change Flask to port 5001: `flask run --port 5001`
