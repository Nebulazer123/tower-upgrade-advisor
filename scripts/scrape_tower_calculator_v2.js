/**
 * Tower Workshop Calculator Scraper V2
 * More robust version with better error handling and timing
 */

const { chromium } = require('playwright');
const fs = require('fs');

// Expected upgrade names for validation
const EXPECTED_UPGRADES = {
  Attack: [
    'Damage', 'Attack Speed', 'Critical Chance', 'Critical Factor', 'Range',
    'Damage / Meter', 'Multishot Chance', 'Multishot Targets', 'Rapid Fire Chance',
    'Rapid Fire Duration', 'Bounce Shot Chance', 'Bounce Shot Targets',
    'Bounce Shot Range', 'Super Crit Chance', 'Super Crit Mult',
    'Rend Armor Chance', 'Rend Armor Mult'
  ],
  Defense: [
    'Health', 'Health Regen', 'Defense Percent', 'Defense Absolute', 'Thorns',
    'Lifesteal', 'Knockback Chance', 'Knockback Force', 'Orb Speed', 'Orbs',
    'Shockwave Size', 'Shockwave Frequency', 'Landmine Chance', 'Landmine Damage',
    'Landmine Radius', 'Death Defy', 'Wall Health', 'Wall Rebuild'
  ],
  Utility: [
    'Cash Bonus', 'Cash / Wave', 'Coins / Kill Bonus', 'Coins / Wave',
    'Free Attack Upgrade', 'Free Defense Upgrade', 'Free Utility Upgrade',
    'Interest / Wave', 'Recovery Amount', 'Max Recovery', 'Package Chance',
    'Enemy Attack Level Skip', 'Enemy Health Level Skip'
  ]
};

const MAX_PAGES_SAFETY = 100; // Increased to capture full dataset (10,000 rows max)

async function waitForStability(page, selector, timeout = 5000) {
  /**
   * Wait for an element to be present and stable (not changing)
   */
  try {
    await page.waitForSelector(selector, { timeout, state: 'visible' });
    await page.waitForTimeout(500); // Extra stability wait
    return true;
  } catch (error) {
    return false;
  }
}

async function scrapeUpgradeData() {
  console.log('🚀 Starting Tower Workshop Calculator scraper V2...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 50
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  
  try {
    // Navigate to the site
    console.log('📍 Navigating to site...');
    await page.goto('https://tower-workshop-calculator.netlify.app/', { 
      waitUntil: 'load',
      timeout: 60000 
    });
    
    // Wait generously for React to render
    console.log('⏳ Waiting for page to initialize...');
    await page.waitForTimeout(5000);
    
    // Check for and handle consent dialog
    console.log('🔍 Checking for consent dialog...');
    const consentCheckbox = page.locator('input[type="checkbox"]').first();
    try {
      await consentCheckbox.waitFor({ state: 'visible', timeout: 5000 });
      console.log('✅ Found consent dialog, checking box...');
      await consentCheckbox.check();
      await page.waitForTimeout(500);
      
      // Click the Continue button
      const continueButton = page.locator('button', { hasText: 'Continue' }).first();
      await continueButton.click();
      console.log('✅ Clicked Continue button');
      await page.waitForTimeout(2000);
    } catch (error) {
      console.log('ℹ️  No consent dialog found, continuing...');
    }
    
    // Navigate to Data section
    console.log('📊 Navigating to Data section...');
    const dataButton = page.locator('button', { hasText: 'Data' }).first();
    await dataButton.waitFor({ state: 'visible', timeout: 15000 });
    await dataButton.click();
    await page.waitForTimeout(1500);
    
    // Click Upgrades tab
    console.log('📦 Clicking Upgrades tab...');
    const upgradesButton = page.locator('button', { hasText: 'Upgrades' }).first();
    await upgradesButton.waitFor({ state: 'visible', timeout: 10000 });
    await upgradesButton.click();
    await page.waitForTimeout(2000);
    
    // Wait for dropdown to appear
    console.log('⏳ Waiting for dropdown...');
    await page.waitForSelector('select', { timeout: 15000 });
    console.log('✅ Ready to scrape!\n');
    
    const result = {
      source: 'tower-workshop-calculator.netlify.app',
      scrapedAt: new Date().toISOString(),
      categories: []
    };
    
    // Process each category
    for (const categoryName of ['Attack', 'Defense', 'Utility']) {
      console.log(`\n${'='.repeat(70)}`);
      console.log(`📂 Processing ${categoryName} category`);
      console.log('='.repeat(70));
      
      // Click category button
      const categoryButton = page.locator('button', { hasText: new RegExp(`^${categoryName}$`) }).first();
      await categoryButton.click();
      await page.waitForTimeout(2000);
      
      // Get all dropdown options
      const dropdown = page.locator('select').first();
      await dropdown.waitFor({ state: 'visible' });
      const options = await dropdown.locator('option').allTextContents();
      
      console.log(`\n✅ Found ${options.length} upgrades:`);
      options.forEach((opt, idx) => console.log(`   ${(idx + 1).toString().padStart(2)}. ${opt}`));
      
      const categoryData = {
        category: categoryName,
        totalUpgrades: options.length,
        upgrades: []
      };
      
      // Process each upgrade
      for (let i = 0; i < options.length; i++) {
        const upgradeName = options[i];
        console.log(`\n  📦 [${i + 1}/${options.length}] ${upgradeName}`);
        
        // Select the upgrade
        await dropdown.selectOption({ index: i });
        await page.waitForTimeout(2000);
        
        // Wait for table to load
        await waitForStability(page, 'table');
        
        const upgradeData = {
          name: upgradeName,
          rows: []
        };
        
        let pageNum = 1;
        let hasMorePages = true;
        
        // Extract table headers (only on first page)
        const headers = await page.locator('table thead th').allTextContents();
        upgradeData.columns = headers.map(h => h.trim());
        console.log(`     Columns: ${upgradeData.columns.join(', ')}`);
        
        // Paginate through all pages
        while (hasMorePages && pageNum <= MAX_PAGES_SAFETY) {
          // Extract table rows
          const rows = await page.locator('table tbody tr').all();
          
          for (const row of rows) {
            const cells = await row.locator('td').allTextContents();
            const rowData = {};
            
            upgradeData.columns.forEach((header, idx) => {
              rowData[header] = cells[idx]?.trim() || '';
            });
            
            upgradeData.rows.push(rowData);
          }
          
          console.log(`     📄 Page ${pageNum}: +${rows.length} rows (total: ${upgradeData.rows.length})`);
          
          // Check if Next button is enabled
          try {
            const nextButton = page.locator('button', { hasText: 'Next' }).first();
            await nextButton.waitFor({ state: 'visible', timeout: 5000 });
            const isDisabled = await nextButton.isDisabled({ timeout: 5000 });
            
            if (isDisabled) {
              hasMorePages = false;
            } else {
              // Click Next
              await nextButton.click();
              await page.waitForTimeout(2000);
              await waitForStability(page, 'table tbody tr');
              pageNum++;
            }
          } catch (error) {
            console.log(`     ⚠️  Next button timeout, assuming last page`);
            hasMorePages = false;
          }
        }
        
        if (pageNum > MAX_PAGES_SAFETY) {
          console.log(`     ⚠️  Hit safety limit!`);
        }
        
        // Calculate stats
        upgradeData.rowsTotal = upgradeData.rows.length;
        upgradeData.maxLevel = upgradeData.rows.length > 0 
          ? parseInt(upgradeData.rows[upgradeData.rows.length - 1].Level || '0') 
          : 0;
        
        console.log(`     ✅ Complete: ${upgradeData.rowsTotal} rows, max level ${upgradeData.maxLevel}`);
        
        categoryData.upgrades.push(upgradeData);
      }
      
      result.categories.push(categoryData);
    }
    
    await browser.close();
    
    // Generate summary
    console.log('\n' + '='.repeat(70));
    console.log('📊 SCRAPING COMPLETE - SUMMARY');
    console.log('='.repeat(70));
    
    for (const category of result.categories) {
      console.log(`\n${category.category} (${category.totalUpgrades} upgrades):`);
      console.log('-'.repeat(70));
      
      for (const upgrade of category.upgrades) {
        const rowStr = upgrade.rowsTotal.toString().padStart(5);
        const levelStr = upgrade.maxLevel.toString().padStart(4);
        console.log(`  ${upgrade.name.padEnd(30)} | ${rowStr} rows | max ${levelStr}`);
      }
    }
    
    const totalUpgrades = result.categories.reduce((sum, cat) => sum + cat.totalUpgrades, 0);
    const totalRows = result.categories.reduce((sum, cat) => 
      sum + cat.upgrades.reduce((s, u) => s + u.rowsTotal, 0), 0);
    
    console.log('\n' + '='.repeat(70));
    console.log(`TOTALS: ${totalUpgrades} upgrades, ${totalRows} total rows`);
    console.log('='.repeat(70));
    
    // Save to file
    const outputPath = 'data/raw/scraped_tower_data.json';
    fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
    console.log(`\n✅ Data saved to: ${outputPath}`);
    
    return result;
    
  } catch (error) {
    console.error('\n❌ Scraper failed:', error.message);
    await page.screenshot({ path: 'error_screenshot.png' });
    console.log('Screenshot saved to: error_screenshot.png');
    await browser.close();
    throw error;
  }
}

scrapeUpgradeData().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
