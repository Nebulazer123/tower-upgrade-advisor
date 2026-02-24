/**
 * Tower Workshop Calculator Scraper
 * 
 * Extracts complete upgrade data from https://tower-workshop-calculator.netlify.app/
 * Handles pagination and validates against expected upgrade lists.
 */

const { chromium } = require('playwright');
const fs = require('fs');

// Expected upgrade names for validation
const EXPECTED_UPGRADES = {
  Attack: [
    'Damage', 'Attack Speed', 'Critical Chance', 'Critical Factor', 'Range',
    'Damage / Meter', 'Multi-shot Chance', 'Multi-shot Targets', 'Rapid Fire Chance',
    'Rapid Fire Duration', 'Bounce Shot Chance', 'Bounce Shot Targets',
    'Bounce Shot Range', 'Super Crit Chance', 'Super Crit Mult',
    'Rend Armor Chance', 'Rend Armor Mult'
  ],
  Defense: [
    'Health', 'Health Regen', 'Defense %', 'Defense Absolute', 'Thorns',
    'Lifesteal', 'Knockback Chance', 'Knockback Force', 'Orb Speed', 'Orbs',
    'Shockwave Size', 'Shockwave Frequency', 'Landmine Chance', 'Landmine Damage',
    'Landmine Radius', 'Death Defy', 'Wall Health', 'Wall Rebuild'
  ],
  Utility: [
    'Cash Bonus', 'Cash / Wave', 'Coin / Kill Bonus', 'Coin / Wave',
    'Free Attack Upgrade', 'Free Defense Upgrade', 'Free Utility Upgrade',
    'Interest / Wave', 'Recovery Amount', 'Max Recovery', 'Package Chance',
    'Enemy Attack Level Skip', 'Enemy Health Level Skip'
  ]
};

const MAX_PAGES_SAFETY = 50; // Safety limit to prevent infinite loops

async function scrapeUpgradeData() {
  console.log('🚀 Starting Tower Workshop Calculator scraper...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 100 // Slow down operations for debugging
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();
  
  // Enable console logging for debugging
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  
  // Navigate to the site
  console.log('📍 Navigating to site...');
  try {
    await page.goto('https://tower-workshop-calculator.netlify.app/', { 
      waitUntil: 'load',
      timeout: 60000 
    });
    console.log('✅ Page loaded');
  } catch (error) {
    console.log('⚠️  Page load timeout, but continuing...');
  }
  
  // Wait for the page to be fully loaded
  console.log('⏳ Waiting for React app to render...');
  await page.waitForTimeout(8000); // Give React more time to render
  
  // Try to find any button to confirm page is interactive
  try {
    await page.waitForSelector('button', { timeout: 15000 });
    console.log('✅ Page is interactive');
  } catch (error) {
    console.log('❌ Page not interactive, taking screenshot...');
    await page.screenshot({ path: 'debug_screenshot.png' });
    const content = await page.content();
    console.log('Page HTML:', content.substring(0, 500));
    throw new Error('Page did not become interactive');
  }
  
  // Click on "Data" tab to navigate to the data section
  console.log('📊 Clicking on Data tab...');
  await page.click('button:has-text("Data")');
  await page.waitForTimeout(1000);
  
  // Click on "Upgrades" sub-tab
  console.log('📦 Clicking on Upgrades tab...');
  await page.click('button:has-text("Upgrades")');
  await page.waitForTimeout(1000);
  
  // Now wait for the dropdown specifically
  try {
    await page.waitForSelector('select', { timeout: 10000 });
    console.log('✅ Dropdown found');
  } catch (error) {
    console.log('❌ Dropdown not found, checking page content...');
    const content = await page.content();
    console.log('Page HTML length:', content.length);
    await page.screenshot({ path: 'debug_screenshot.png' });
    throw new Error('Dropdown not found on page');
  }
  
  const result = {
    source: 'tower-workshop-calculator.netlify.app',
    scrapedAt: new Date().toISOString(),
    categories: []
  };
  
  // Process each category
  for (const categoryName of ['Attack', 'Defense', 'Utility']) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📂 Processing ${categoryName} category`);
    console.log('='.repeat(60));
    
    // Click category button - find button with exact text match
    const categoryButton = page.locator('button').filter({ hasText: new RegExp(`^${categoryName}$`) });
    await categoryButton.click();
    await page.waitForTimeout(1500);
    
    // Get all dropdown options
    const dropdown = await page.locator('select').first();
    const options = await dropdown.locator('option').allTextContents();
    
    console.log(`\n✅ Found ${options.length} upgrades in ${categoryName}:`);
    options.forEach((opt, idx) => console.log(`   ${idx + 1}. ${opt}`));
    
    // Validate against expected list
    const expected = EXPECTED_UPGRADES[categoryName];
    const missing = expected.filter(exp => !options.some(opt => 
      opt.toLowerCase().includes(exp.toLowerCase()) || 
      exp.toLowerCase().includes(opt.toLowerCase())
    ));
    const extra = options.filter(opt => !expected.some(exp => 
      opt.toLowerCase().includes(exp.toLowerCase()) || 
      exp.toLowerCase().includes(opt.toLowerCase())
    ));
    
    if (missing.length > 0) {
      console.log(`\n⚠️  Missing from expected list: ${missing.join(', ')}`);
    }
    if (extra.length > 0) {
      console.log(`\n⚠️  Extra/renamed items: ${extra.join(', ')}`);
    }
    
    const categoryData = {
      category: categoryName,
      totalUpgrades: options.length,
      upgrades: []
    };
    
    // Process each upgrade
    for (let i = 0; i < options.length; i++) {
      const upgradeName = options[i];
      console.log(`\n  📦 Scraping: ${upgradeName} (${i + 1}/${options.length})`);
      
      // Select the upgrade
      await dropdown.selectOption({ index: i });
      await page.waitForTimeout(1000); // Wait for table to load
      
      const upgradeData = {
        name: upgradeName,
        rows: []
      };
      
      let pageNum = 1;
      let hasMorePages = true;
      
      // Paginate through all pages
      while (hasMorePages && pageNum <= MAX_PAGES_SAFETY) {
        console.log(`    📄 Page ${pageNum}...`);
        
        // Wait for table to be visible
        await page.waitForSelector('table', { timeout: 5000 });
        
        // Extract table headers (only on first page)
        if (pageNum === 1) {
          const headers = await page.locator('table thead th').allTextContents();
          upgradeData.columns = headers.map(h => h.trim());
        }
        
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
        
        console.log(`       ✓ Extracted ${rows.length} rows`);
        
        // Check if Next button is enabled
        const nextButton = page.locator('button:has-text("Next")');
        const isDisabled = await nextButton.isDisabled();
        
        if (isDisabled) {
          hasMorePages = false;
          console.log(`       ℹ️  Last page reached`);
        } else {
          // Click Next
          await nextButton.click();
          await page.waitForTimeout(1000);
          pageNum++;
        }
      }
      
      if (pageNum > MAX_PAGES_SAFETY) {
        console.log(`    ⚠️  WARNING: Hit safety limit of ${MAX_PAGES_SAFETY} pages!`);
      }
      
      // Calculate stats
      upgradeData.rowsTotal = upgradeData.rows.length;
      upgradeData.maxLevel = upgradeData.rows.length > 0 
        ? parseInt(upgradeData.rows[upgradeData.rows.length - 1].Level || '0') 
        : 0;
      
      console.log(`    ✅ Complete: ${upgradeData.rowsTotal} total rows, max level ${upgradeData.maxLevel}`);
      
      // Validate data
      if (upgradeData.rowsTotal === 0) {
        console.log(`    ❌ ERROR: No rows extracted for ${upgradeName}!`);
      }
      
      // Validate level continuity
      const levels = upgradeData.rows.map(r => parseInt(r.Level || '0'));
      for (let j = 1; j < levels.length; j++) {
        if (levels[j] !== levels[j-1] + 1) {
          console.log(`    ⚠️  WARNING: Level gap detected: ${levels[j-1]} -> ${levels[j]}`);
        }
      }
      
      categoryData.upgrades.push(upgradeData);
    }
    
    result.categories.push(categoryData);
  }
  
  await browser.close();
  
  // Generate summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 SCRAPING SUMMARY');
  console.log('='.repeat(60));
  
  let totalUpgrades = 0;
  let totalRows = 0;
  
  for (const category of result.categories) {
    console.log(`\n${category.category} (${category.totalUpgrades} upgrades):`);
    console.log('-'.repeat(60));
    
    for (const upgrade of category.upgrades) {
      console.log(`  ${upgrade.name.padEnd(30)} | ${upgrade.rowsTotal.toString().padStart(5)} rows | max level ${upgrade.maxLevel}`);
      totalUpgrades++;
      totalRows += upgrade.rowsTotal;
    }
  }
  
  console.log('\n' + '='.repeat(60));
  console.log(`TOTALS: ${totalUpgrades} upgrades, ${totalRows} total rows`);
  console.log('='.repeat(60));
  
  // Save to file
  const outputPath = 'scraped_tower_data.json';
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.log(`\n✅ Data saved to: ${outputPath}`);
  
  return result;
}

// Run the scraper
scrapeUpgradeData().catch(error => {
  console.error('❌ Scraper failed:', error);
  process.exit(1);
});
