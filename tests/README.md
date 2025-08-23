# Tests Directory

This directory contains all automated tests for the Sri Lanka RSI Monitor project.

## Structure

```
tests/
├── __init__.py                # Makes tests a Python package
├── test_scraper.py           # Python unit tests for scraper functionality  
├── test_dashboard.html       # HTML/JavaScript tests for dashboard
└── README.md                # This file
```

## Test Types

### Unit Tests (`test_scraper.py`)
- **Purpose**: Test individual functions and components
- **Technology**: Python unittest + pytest
- **Coverage**: Scraper logic, data validation, file generation
- **Critical Tests**: RSI threshold validation (< 50 oversold)

### Frontend Tests (`test_dashboard.html`)  
- **Purpose**: Test dashboard functionality and UI logic
- **Technology**: Custom JavaScript test framework
- **Coverage**: RSI calculations, filtering, DOM manipulation
- **Critical Tests**: Ensures correct thresholds in UI

## Running Tests

### All Python Tests
```bash
# From project root
python -m pytest tests/

# With verbose output
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=daily_rsi_scraper
```

### Specific Test File
```bash
python -m pytest tests/test_scraper.py -v
```

### HTML/JS Tests
```bash
# Open in browser
open tests/test_dashboard.html

# Headless with Playwright (if configured)
npx playwright test tests/test_dashboard.html
```

## Test Configuration

- **pytest.ini**: Test discovery and default options
- **requirements.txt**: Testing dependencies  
- **.github/workflows/test.yml**: CI/CD automation

## Critical Validations

🚨 **RSI Threshold Protection**: Tests ensure oversold threshold remains `< 50`
- Any attempt to change to `< 30` will fail tests
- Both Python and JavaScript logic are validated
- CI/CD blocks merges if threshold tests fail

## Adding New Tests

1. **Python Tests**: Add methods to `TestRSIScraper` class
2. **JavaScript Tests**: Add to test framework in `test_dashboard.html`
3. **Integration Tests**: Consider adding separate test file

Follow naming convention: `test_*` for functions/methods.

## Test Markers

Use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_basic_functionality():
    pass

@pytest.mark.critical  
def test_rsi_threshold():
    pass
```

Run specific markers:
```bash
python -m pytest -m "critical"
```