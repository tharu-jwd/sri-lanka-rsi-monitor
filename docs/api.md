# API Reference

The Sri Lanka RSI Monitor provides JSON API access through the `latest_rsi.json` file, updated daily with fresh RSI data.

## Base URL

The API is accessible at:
```
https://github.com/tharu-jwd/sri-lanka-rsi-monitor/latest_rsi.json
```

## Response Format

### Root Object

```json
{
  "metadata": {
    "date": "2025-08-22",
    "timestamp": "2025-08-22T11:40:13.553260",
    "timeframes": ["1D", "1W", "1M"],
    "total_symbols": 304,
    "successful_fetches": 296,
    "failed_fetches": 8,
    "success_rate": 97.36842105263158,
    "timeframe_stats": { /* ... */ },
    "scraper_config": { /* ... */ },
    "version": "2.0"
  },
  "data": { /* Stock data objects */ }
}
```

### Metadata Object

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Data collection date (YYYY-MM-DD) |
| `timestamp` | string | ISO 8601 timestamp of data collection |
| `timeframes` | array | Available timeframes ["1D", "1W", "1M"] |
| `total_symbols` | number | Total number of symbols processed |
| `successful_fetches` | number | Successfully collected symbols |
| `failed_fetches` | number | Failed collection attempts |
| `success_rate` | number | Success percentage (0-100) |
| `timeframe_stats` | object | Per-timeframe success statistics |
| `scraper_config` | object | Scraper configuration used |
| `version` | string | API version |

### Timeframe Statistics

```json
"timeframe_stats": {
  "1D": {
    "successful": 296,
    "total": 296,
    "success_rate": 100.0
  },
  "1W": {
    "successful": 295,
    "total": 296,
    "success_rate": 99.66
  },
  "1M": {
    "successful": 289,
    "total": 296,
    "success_rate": 97.64
  }
}
```

### Stock Data Object

Each stock in the `data` object:

```json
"CSELK-ABAN.N0000": {
  "rsi_data": {
    "1D": 81.91,
    "1W": 94.57,
    "1M": 88.85
  },
  "status": "success",
  "successful_timeframes": 3,
  "timestamp": "2025-08-22T09:25:43.413501",
  "attempts": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rsi_data` | object | RSI values by timeframe |
| `status` | string | "success" or "failed" |
| `successful_timeframes` | number | Count of successful timeframes |
| `timestamp` | string | When this stock was processed |
| `attempts` | number | Number of retry attempts made |

### RSI Data Values

- **Type**: `number` or `null`
- **Range**: 0-100 (when not null)
- **null**: Indicates data unavailable for that timeframe

