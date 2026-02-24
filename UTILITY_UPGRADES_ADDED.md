# Utility Upgrades Added

## Problem Identified

The Tower Upgrade Advisor was missing the **utility** category entirely. The data source (GitHub repository `jacoelt/tower-calculator`) only contained:
- **9 Attack upgrades** (damage, attack speed, crit chance, crit factor, multishot, rapid fire, bounce shot)
- **4 Defense upgrades** (health, health regen, defense percent, defense absolute)
- **0 Utility upgrades** ❌

The actual game has three workshop categories: Attack, Defense, and **Utility**.

## Solution Implemented

### 1. Data Sources Investigated
- **GitHub repo** (`jacoelt/tower-calculator`): Contains only attack and defense upgrades
- **Netlify calculator** (`tower-workshop-calculator.netlify.app`): Has all three categories but scraping produced corrupted data
- **Game wikis**: Found detailed information for some utility upgrades

### 2. Utility Upgrades Added

Created `scripts/add_utility_upgrades.py` to add 8 utility upgrades:

| Upgrade | Levels | Effect Type | Description |
|---------|--------|-------------|-------------|
| **Cash Bonus** | 149 | Multiplicative | Increases cash production (1.0x → 2.49x) |
| **Cash / Wave** | 149 | Additive | Cash earned after completing a wave (0 → 596) |
| **Coins / Kill Bonus** | 100 | Additive | Bonus coins from defeating enemies (0% → 50%) |
| **Coins / Wave** | 100 | Additive | Coins earned at wave completion (0 → 200) |
| **Interest / Wave** | 99 | Additive | Passive income based on cash on hand (0% → 5.94%) |
| **Free Attack Upgrade** | 20 | Additive | Free attack workshop upgrades |
| **Free Defense Upgrade** | 20 | Additive | Free defense workshop upgrades |
| **Free Utility Upgrade** | 20 | Additive | Free utility workshop upgrades |

### 3. Current Status

✅ **Working**: The app now recognizes all three categories:
- Attack: 9 upgrades
- Defense: 4 upgrades  
- Utility: 8 upgrades
- **Total: 21 upgrades**

✅ **Validated**: Schema validation passes
✅ **Tested**: 42/43 tests pass (1 unrelated Windows file system test failure)

## Data Quality Notes

⚠️ **Placeholder Data**: The utility upgrade data is based on:
- Wiki research for Interest/Wave (accurate)
- Estimated formulas for other upgrades (approximations)

The coin costs and some effect values are **estimates** based on typical Tower game progression patterns. For production use, the data should be refined with:
1. Actual game data extraction
2. Community-verified values
3. Or manual data entry from in-game observations

## Files Modified/Created

- `scripts/add_utility_upgrades.py` - New script to add utility upgrades
- `data/upgrades.json` - Now contains 21 upgrades (was 13)
- `scripts/parse_github_data.py` - Unchanged (still only parses attack/defense)
- `scripts/extract_data.py` - Attempted to use but produced corrupted data

## How to Update/Improve

To improve the utility upgrade data:

1. **Manual entry**: Play the game and record actual values
2. **Community data**: Check Tower Discord/Reddit for data sheets
3. **Fix Netlify scraper**: Debug why the scraper produces garbled text
4. **Alternative sources**: Look for other Tower calculators or data repositories

## Usage

The utility upgrades are now fully integrated:

```python
from src.data_loader import load_upgrades
from src.scoring import BalancedEngine

db = load_upgrades()
engine = BalancedEngine()

# Utility upgrades will now appear in rankings
profile = Profile(...)
ranked = engine.rank(profile, db)
```

The BalancedEngine allows users to adjust weights for each category, including utility.
