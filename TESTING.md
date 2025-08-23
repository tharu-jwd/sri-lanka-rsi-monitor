# Testing Guide for Sri Lanka RSI Monitor

## Overview

This project includes comprehensive automated testing to ensure code quality and prevent regressions, especially for critical RSI thresholds.

## Test Structure

### 1. Python Unit Tests (`tests/test_scraper.py`)

Tests the core scraper functionality:

- ✅ **RSI Threshold Validation**: Ensures oversold threshold is `< 50` (NOT `< 30`)
- ✅ **Data Integrity**: Validates stock data structure and company mappings
- ✅ **Scraper Logic**: Tests URL building, batch processing, data saving
- ✅ **File Generation**: Validates JSON and HTML output structure
- ✅ **Error Handling**: Tests driver creation and failure scenarios

**Run locally:**
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_scraper.py -v

# Run with coverage
python -m pytest tests/ --cov=daily_rsi_scraper
```

### 2. HTML/JavaScript Tests (`tests/test_dashboard.html`)

Tests the dashboard functionality:

- ✅ **Critical RSI Thresholds**: Validates `< 50` oversold, `> 70` overbought  
- ✅ **Filtering Logic**: Tests stock filtering by RSI categories
- ✅ **Multi-timeframe Support**: Validates 1D, 1W, 1M timeframe switching
- ✅ **DOM Elements**: Ensures required HTML elements exist
- ✅ **Data Structure**: Validates stock data array format
- ✅ **Edge Cases**: Tests boundary RSI values (0, 50, 70, 100)

**Run locally:**
```bash
# Open in browser
open tests/test_dashboard.html

# Or use headless testing with Playwright
npx playwright test tests/test_dashboard.html
```

### 3. GitHub Actions Workflow (`.github/workflows/test.yml`)

Automated CI/CD pipeline with multiple jobs:

#### `python-tests`
- Runs Python unit tests
- Validates stock data integrity  
- Uses Python 3.9 with Chrome for Selenium testing

#### `html-javascript-tests`
- Uses Playwright for headless browser testing
- Validates dashboard functionality
- Checks critical RSI threshold tests pass

#### `html-structure-validation`
- **Critical Check**: Ensures `< 50` threshold exists in HTML
- **Critical Check**: Ensures `< 30` threshold does NOT exist
- Validates required DOM elements
- Pure bash validation (no dependencies)

#### `json-validation`
- Validates JSON structure and syntax
- Checks required metadata fields
- Validates timeframes array

#### `security-scan`
- Scans for sensitive data patterns
- Checks for hardcoded credentials
- Prevents accidental key exposure

#### `requirements-check`
- Validates Python dependencies
- Creates requirements.txt if missing
- Tests import capabilities

## Setting Up Branch Protection

### Step 1: Create Branch Protection Rule

1. Go to your GitHub repository
2. Navigate to **Settings** → **Branches**
3. Click **Add rule** or **Add branch protection rule**
4. Set **Branch name pattern**: `main`

### Step 2: Configure Protection Settings

Enable these settings:

```
☑️ Require a pull request before merging
  ☑️ Require approvals (1)
  ☑️ Dismiss stale PR approvals when new commits are pushed
  ☑️ Require review from code owners

☑️ Require status checks to pass before merging
  ☑️ Require branches to be up to date before merging
  
  Required status checks:
  ☑️ python-tests
  ☑️ html-javascript-tests  
  ☑️ html-structure-validation
  ☑️ json-validation
  ☑️ security-scan
  ☑️ requirements-check

☑️ Require conversation resolution before merging
☑️ Include administrators
```

### Step 3: Test the Protection

1. Create a test branch: `git checkout -b test-protection`
2. Make a small change
3. Push and create a PR
4. Verify all tests run and must pass before merge

## Critical Validations

### 🚨 RSI Threshold Protection

The tests specifically protect against changing the oversold threshold:

- ✅ **Must use `< 50`** for oversold detection
- ❌ **Must NOT use `< 30`** (will fail tests)
- Tests validate both Python logic and HTML/JavaScript

### Example Test Failure

If someone tries to change the threshold to `< 30`:

```bash
❌ ERROR: Wrong oversold threshold (< 30) found!
Process exited with code 1
```

## Running All Tests Locally

### Prerequisites
```bash
pip install -r requirements.txt
npm install -D playwright
npx playwright install chromium
```

### Run Python Tests
```bash
python -m pytest tests/ -v --tb=short
```

### Run HTML/JS Tests  
```bash
npx playwright test --config playwright.config.js
# OR open tests/test_dashboard.html in browser
```

### Run Structure Validation
```bash
# Check HTML structure
grep -q "rsiValue < 50" index.html && echo "✅ Correct threshold" || echo "❌ Wrong threshold"

# Check no wrong threshold
! grep -q "rsiValue < 30" index.html && echo "✅ No wrong threshold" || echo "❌ Wrong threshold found"
```

## Monitoring Test Results

### GitHub Actions Status

- **Green ✅**: All tests passed, safe to merge
- **Red ❌**: Tests failed, PR blocked
- **Yellow ⏳**: Tests running

### Pull Request Checks

Each PR shows status for all test jobs:

```
✅ python-tests — Tests passed
✅ html-structure-validation — HTML validation passed  
✅ json-validation — JSON structure valid
❌ security-scan — Sensitive data detected
```

## Troubleshooting

### Common Issues

1. **Selenium Tests Fail**
   - Ensure Chrome is installed
   - Check ChromeDriver compatibility
   - Verify network connectivity for TradingView

2. **HTML Tests Fail**  
   - Check if threshold was accidentally changed
   - Verify DOM element IDs haven't changed
   - Ensure JavaScript syntax is valid

3. **JSON Validation Fails**
   - Check JSON syntax with `python -m json.tool file.json`
   - Verify required metadata fields exist
   - Ensure data structure matches expected format

### Debug Mode

Add debug output to tests:
```python
# In test_scraper.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Adding New Tests

### Python Tests
Add to `tests/test_scraper.py`:
```python
def test_new_functionality(self):
    # Test implementation
    self.assertEqual(expected, actual)
```

### HTML/JS Tests  
Add to `tests/test_dashboard.html`:
```javascript
testRunner.test('New Feature Test', () => {
    // Test implementation
    testRunner.assert(condition, 'Error message');
});
```

### GitHub Actions
Add new job to `.github/workflows/test.yml`:
```yaml
new-test-job:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run new test
      run: echo "Test command"
```

Remember: All tests must pass for PR merge! 🛡️