# Sri Lanka RSI Monitor

A comprehensive RSI (Relative Strength Index) monitoring system for Sri Lankan stocks listed on the Colombo Stock Exchange (CSE). Features automated data collection, multi-timeframe analysis, and an interactive web dashboard.

## Features

### Multi-Timeframe Analysis
- **1 Day RSI**: Short-term momentum analysis
- **1 Week RSI**: Medium-term trend analysis  
- **1 Month RSI**: Long-term trend analysis

### Interactive Dashboard
- Real-time RSI data for 300+ Sri Lankan stocks
- Interactive filtering (Oversold < 50, Neutral 50-70, Overbought > 70)
- Sortable columns and responsive design
- Mobile-friendly interface

### Automated Data Collection
- Daily scraping from TradingView
- GitHub Actions automation
- High success rate (95%+)
- Error handling and retry logic

## Quick Start

### Prerequisites
- Python 3.9+
- Chrome browser (for scraping)

### Installation

```bash
# Clone the repository
git clone https://github.com/tharu-jwd/sri-lanka-rsi-monitor.git
cd sri-lanka-rsi-monitor

# Install dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

### Usage

#### Run the Scraper
```bash
# Basic usage
python daily_rsi_scraper.py

# With custom settings
python daily_rsi_scraper.py --batch-size 25 --rate-limit 3.0

# GitHub Actions optimized
python daily_rsi_scraper.py --github-actions
```

#### View the Dashboard
Open `index.html` in your browser or serve it locally:
```bash
python -m http.server 8000
# Open http://localhost:8000
```

## Project Structure

```
sri-lanka-rsi-monitor/
├── daily_rsi_scraper.py       # Main scraper script
├── index.html                 # Interactive dashboard
├── latest_rsi.json           # Current RSI data (API)
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── pytest.ini               # Test configuration
├── TESTING.md               # Testing documentation
├── .github/workflows/       # GitHub Actions
│   └── test.yml            # CI/CD pipeline
└── tests/                  # Test suite
    ├── test_scraper.py     # Python unit tests
    └── test_dashboard.html # Frontend tests
```

## RSI Interpretation

### Thresholds
- **Oversold (< 50)**: Potentially undervalued, buying opportunity
- **Neutral (50-70)**: Normal trading range
- **Overbought (> 70)**: Potentially overvalued, selling opportunity

### Multi-Timeframe Strategy
- **1D**: Day trading and short-term entries
- **1W**: Swing trading and medium-term trends
- **1M**: Long-term investment decisions

## Data Sources

- **Primary**: TradingView technical indicators
- **Coverage**: 300+ CSE listed companies
- **Update Frequency**: Daily at 5:00 PM Sri Lanka time
- **Timeframes**: 1D, 1W, 1M RSI values

## API Access

### JSON Endpoint
The `latest_rsi.json` file provides programmatic access:

```javascript
{
  "metadata": {
    "date": "2025-08-22",
    "timeframes": ["1D", "1W", "1M"],
    "success_rate": 97.4
  },
  "data": {
    "CSELK-ABAN.N0000": {
      "rsi_data": {
        "1D": 81.91,
        "1W": 94.57,
        "1M": 88.85
      },
      "status": "success"
    }
  }
}
```

## Configuration

### Environment Variables
```bash
# Scraper settings
BATCH_SIZE=50           # Stocks per batch
MAX_WORKERS=1          # Parallel workers
RATE_LIMIT=2.0         # Delay between requests
RETRY_COUNT=3          # Retry attempts
```

### Command Line Options
```bash
python daily_rsi_scraper.py --help

Options:
  --batch-size INTEGER    Number of stocks per batch (default: 50)
  --max-workers INTEGER   Maximum parallel workers (default: 1)
  --rate-limit FLOAT     Rate limit delay in seconds (default: 2.0)
  --retry-count INTEGER   Number of retry attempts (default: 3)
  --max-stocks INTEGER    Maximum stocks to process
  --resume-from INTEGER   Resume from stock index
  --github-actions       GitHub Actions optimizations
```

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=daily_rsi_scraper

# Run specific test
python -m pytest tests/test_scraper.py -v
```

### Code Quality
```bash
# Format code
black daily_rsi_scraper.py

# Lint code
flake8 daily_rsi_scraper.py

# Type checking
mypy daily_rsi_scraper.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run test suite
5. Submit pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Testing

Comprehensive test suite protects critical functionality:
- Python unit tests for scraper logic
- Frontend tests for dashboard
- CI/CD pipeline with 6 test jobs
- Critical RSI threshold validation

See [TESTING.md](TESTING.md) for testing documentation.

## Performance

### Benchmarks
- **Coverage**: 300+ stocks across 3 timeframes
- **Success Rate**: 95-98% data collection
- **Runtime**: ~15-20 minutes for full scrape
- **Memory Usage**: < 500MB during execution

### Optimizations
- Rate limiting to avoid blocking
- Batch processing for efficiency
- Retry logic for reliability
- Chrome headless mode for speed

## Disclaimer

This tool is for educational and informational purposes only. Not financial advice. Past performance does not guarantee future results. Always do your own research before making investment decisions.
