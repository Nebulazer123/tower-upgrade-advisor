# Tower Workshop Calculator Scraper

This script extracts the complete upgrade dataset from https://tower-workshop-calculator.netlify.app/

## Installation

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install chromium
```

## Usage

### Local Execution

```bash
npm run scrape
```

The script will:
1. Open a browser window (headless: false for debugging)
2. Navigate through all three categories (Attack, Defense, Utility)
3. Extract all dropdown options and validate against expected lists
4. Scrape all table data with full pagination
5. Save results to `scraped_tower_data.json`

### With Browserbase

If you want to use Browserbase instead of local Playwright:

```javascript
// Modify the script to connect to Browserbase
const browser = await chromium.connectOverCDP(
  `wss://connect.browserbase.com?apiKey=${process.env.BROWSERBASE_API_KEY}`
);
```

## Output Format

The script generates a JSON file with this structure:

```json
{
  "source": "tower-workshop-calculator.netlify.app",
  "scrapedAt": "2026-02-20T...",
  "categories": [
    {
      "category": "Attack",
      "totalUpgrades": 17,
      "upgrades": [
        {
          "name": "Damage",
          "columns": ["Level", "Value", "Next Coins", ...],
          "rows": [
            {"Level": "1", "Value": "10", "Next Coins": "100", ...},
            ...
          ],
          "rowsTotal": 2500,
          "maxLevel": 2500
        }
      ]
    }
  ]
}
```

## Validation

The script performs several validation checks:

1. **Dropdown Verification**: Compares found upgrades against expected lists
2. **Row Count**: Ensures each upgrade has > 0 rows
3. **Level Continuity**: Checks for gaps in level sequences
4. **Pagination Safety**: Limits to 50 pages max to prevent infinite loops

## Expected Upgrade Counts

- **Attack**: 17 upgrades
- **Defense**: 18 upgrades  
- **Utility**: 13 upgrades
- **Total**: 48 upgrades

## Troubleshooting

### Script hangs on pagination
- Check the `MAX_PAGES_SAFETY` constant (default: 50)
- Increase `waitForTimeout` values if the site is slow

### Missing upgrades
- Check console output for validation warnings
- The script will report missing/extra/renamed items

### Table extraction fails
- Ensure the site structure hasn't changed
- Check table selectors: `table thead th` and `table tbody tr`

## Performance

Expected runtime: ~10-15 minutes for all 48 upgrades (depending on pagination depth)
