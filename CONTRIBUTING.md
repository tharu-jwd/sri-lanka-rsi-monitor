# Contributing to Sri Lanka RSI Monitor

Thank you for considering contributing to the Sri Lanka RSI Monitor! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Documentation](#documentation)

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Chrome browser
- Basic knowledge of web scraping and HTML/CSS/JavaScript

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/sri-lanka-rsi-monitor.git
   cd sri-lanka-rsi-monitor
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Verify Setup**
   ```bash
   python -m pytest tests/
   python daily_rsi_scraper.py --help
   ```

## Development Process

### Workflow

1. **Create Issue**: For bugs or feature requests
2. **Create Branch**: `git checkout -b feature/your-feature-name`
3. **Develop**: Make changes with tests
4. **Test**: Ensure all tests pass
5. **Document**: Update documentation
6. **Submit PR**: Create pull request

### Branch Naming

- `feature/add-new-indicator` - New features
- `fix/scraper-timeout-issue` - Bug fixes
- `docs/api-documentation` - Documentation updates
- `test/improve-coverage` - Test improvements

## Coding Standards

### Python Code Style

Follow PEP 8 with these specifics:

```python
# Good
def fetch_rsi_data(symbol: str, timeframe: str) -> Optional[float]:
    """Fetch RSI data for given symbol and timeframe.
    
    Args:
        symbol: Stock symbol (e.g., 'CSELK-ABAN.N0000')
        timeframe: Timeframe ('1D', '1W', '1M')
        
    Returns:
        RSI value or None if failed
    """
    pass

# Bad
def fetchRSIData(symbol,timeframe):
    pass
```

### HTML/CSS/JavaScript

```html
<!-- Good: Semantic HTML with proper indentation -->
<div class="rsi-container">
    <h2 class="rsi-header">RSI Analysis</h2>
    <table class="rsi-table" id="rsiTable">
        <!-- Content -->
    </table>
</div>
```

```javascript
// Good: Clear variable names and comments
function calculateRSICategory(rsiValue) {
    if (rsiValue < 50) return 'oversold';
    if (rsiValue > 70) return 'overbought';
    return 'neutral';
}
```

### Documentation Standards

- All functions must have docstrings
- Complex logic requires inline comments
- README updates for new features
- API documentation for public interfaces

## Testing Requirements

### Critical Rule: RSI Thresholds

**NEVER change the RSI thresholds without discussion:**
- Oversold: < 50 (NOT < 30)
- Overbought: > 70
- Neutral: 50-70

Any PR that changes these thresholds will be automatically rejected by CI/CD.

### Test Coverage

All contributions must include tests:

#### Python Changes
```python
# tests/test_scraper.py
def test_new_feature(self):
    """Test description."""
    # Arrange
    scraper = EnhancedMultiTimeframeRSIScraper(url, symbols)
    
    # Act
    result = scraper.new_method()
    
    # Assert
    self.assertEqual(expected, result)
```

#### Frontend Changes
```javascript
// tests/test_dashboard.html
testRunner.test('New Dashboard Feature', () => {
    // Test implementation
    const result = newFunction();
    testRunner.assertEqual(result, expected);
});
```

### Running Tests

Before submitting PR:
```bash
# Run all tests
python -m pytest tests/ -v

# Check test coverage
python -m pytest tests/ --cov=daily_rsi_scraper

# Test HTML/JS functionality
open tests/test_dashboard.html
```

## Pull Request Process

### Before Submitting

1. **Update Documentation**: README, docstrings, comments
2. **Run Tests**: All tests must pass
3. **Check Style**: Follow coding standards
4. **Update CHANGELOG**: Add your changes
5. **Rebase**: `git rebase main` to get latest changes

### PR Description Template

```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Test improvement

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Documentation
- [ ] README updated
- [ ] Docstrings added/updated
- [ ] Comments added for complex logic

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] No breaking changes (or documented)
- [ ] Ready for review
```

### Review Process

1. **Automated Checks**: CI/CD must pass
2. **Code Review**: Maintainer review required  
3. **Testing**: Manual testing if needed
4. **Documentation**: Check docs are complete
5. **Merge**: Squash merge preferred

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g. macOS 12.0]
- Python: [e.g. 3.9.7]
- Browser: [e.g. Chrome 96.0]

**Additional Context**
Screenshots, logs, etc.
```

### Feature Requests

```markdown
**Feature Description**
Clear description of desired feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches you've thought of

**Additional Context**
Mockups, examples, etc.
```

## Documentation

### When to Update Documentation

- Adding new features
- Changing existing functionality
- Fixing bugs that affect user behavior
- Adding configuration options

### Documentation Types

1. **README.md**: Overview and quick start
2. **API Documentation**: Function/class documentation
3. **User Guides**: Step-by-step tutorials
4. **Developer Docs**: Internal architecture
5. **CHANGELOG.md**: Version history

### Writing Style

- Use clear, concise language
- Include code examples
- Provide step-by-step instructions
- Use consistent formatting
- Test all examples

## Development Guidelines

### Performance Considerations

- Rate limiting to avoid being blocked
- Efficient data structures
- Memory usage optimization
- Async operations where appropriate

### Security Best Practices

- No hardcoded credentials
- Validate all user inputs
- Sanitize data before display
- Use HTTPS for all external requests

### Error Handling

```python
# Good: Specific error handling
try:
    rsi_value = fetch_rsi_data(symbol)
except TimeoutError:
    logger.warning(f"Timeout fetching {symbol}")
    return None
except ValueError as e:
    logger.error(f"Invalid RSI data for {symbol}: {e}")
    return None

# Bad: Generic exception handling
try:
    rsi_value = fetch_rsi_data(symbol)
except Exception:
    return None
```

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

1. Update version numbers
2. Update CHANGELOG.md
3. Run full test suite
4. Create release branch
5. Tag release
6. Deploy to production
7. Update documentation

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Sri Lanka RSI Monitor!