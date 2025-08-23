# Changelog

All notable changes to the Sri Lanka RSI Monitor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation suite
- API reference documentation
- Deployment guides for multiple platforms
- Troubleshooting guide with common solutions

## [2.0.0] - 2025-08-22

### Added
- Comprehensive testing framework with Python unit tests and HTML/JS tests
- GitHub Actions CI/CD pipeline with 6 automated test jobs
- Critical RSI threshold protection (< 50 oversold) with automated validation
- pytest configuration and structured test directory
- Security scanning and data validation in CI/CD
- Development and production requirements separation
- Test documentation and contribution guidelines

### Changed
- Reorganized project structure with standard testing layout
- Separated production and development dependencies
- Enhanced error handling and retry logic in scraper
- Improved batch processing for better stability

### Security
- Added automated security scanning for sensitive data
- Implemented branch protection with required status checks
- Added validation to prevent threshold changes without review

## [1.0.0] - 2025-08-18

### Added
- Multi-timeframe RSI scraper for Sri Lankan stocks (1D, 1W, 1M)
- Interactive HTML dashboard with filtering and sorting
- Automated data collection from TradingView
- JSON API endpoint for programmatic access
- Support for 300+ stocks from Colombo Stock Exchange
- Rate limiting and error handling for stable scraping
- Responsive design for mobile and desktop
- GitHub Actions workflow for automated deployment

### Features
- **RSI Analysis**: Real-time RSI calculation for multiple timeframes
- **Interactive Dashboard**: Click-to-filter by oversold/overbought/neutral
- **High Success Rate**: 95%+ data collection reliability
- **Mobile Friendly**: Responsive design works on all devices
- **API Access**: JSON endpoint for developers
- **Automated Updates**: Daily data collection via GitHub Actions

### Technical Details
- **Data Source**: TradingView technical indicators
- **Browser Automation**: Selenium WebDriver with Chrome
- **Update Schedule**: Daily at 5:00 PM Sri Lanka time
- **Output Formats**: Interactive HTML + JSON API

## [0.1.0] - Initial Development

### Added
- Basic web scraping functionality
- Simple HTML output
- Single timeframe RSI collection

---

## Release Process

### Version Numbering
- **MAJOR** (X.0.0): Breaking changes, major feature additions
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, minor improvements

### Release Checklist
- [ ] Update version in relevant files
- [ ] Update CHANGELOG.md with release notes
- [ ] Run full test suite
- [ ] Tag release in Git
- [ ] Create GitHub release
- [ ] Deploy to production
- [ ] Update documentation if needed

### Breaking Changes
Breaking changes are documented with clear migration instructions:

#### From 1.x to 2.x
- **Testing**: New test requirements for contributions
- **Dependencies**: Separated dev and production requirements
- **CI/CD**: New GitHub Actions workflow with required checks

### Migration Guide

#### Upgrading to 2.0.0
1. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt  # Production
   pip install -r requirements-dev.txt  # Development
   ```

2. **Run Tests**:
   ```bash
   python -m pytest tests/
   ```

3. **Update GitHub Settings**:
   - Enable branch protection rules
   - Require status checks to pass
   - Configure required reviewers

#### Development Workflow Changes
- All PRs must pass automated tests
- Branch protection prevents direct pushes to main
- RSI threshold changes are automatically blocked

### Contributing to Releases

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to propose new features
- Release candidate testing
- Documentation updates
- Breaking change discussions