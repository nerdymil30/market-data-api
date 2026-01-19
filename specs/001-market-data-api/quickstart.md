# Quickstart: Market Data API Library

**Feature**: 001-market-data-api
**Date**: 2026-01-19

## Installation

```bash
# Clone the repository
cd /path/to/market-data-api

# Install in development mode
pip install -e .

# Install Playwright for cookie capture (optional, only for Barchart)
playwright install chromium
```

## Configuration

### 1. Create Config Directory

```bash
mkdir -p ~/.config/market-data
```

### 2. Set Up Credentials

**For Tiingo** (recommended for getting started):

```bash
cat > ~/.config/market-data/credentials.json << 'EOF'
{
  "tiingo_api_key": "YOUR_TIINGO_API_KEY"
}
EOF
```

Get a free API key at: https://www.tiingo.com/

**For Barchart** (requires account):

```bash
cat > ~/.config/market-data/credentials.json << 'EOF'
{
  "tiingo_api_key": "YOUR_TIINGO_API_KEY",
  "barchart_username": "your.email@example.com",
  "barchart_password_env": "BARCHART_PASSWORD"
}
EOF

# Set password in environment
export BARCHART_PASSWORD="your-password"

# Capture initial cookies
python -m market_data.refresh.capture_cookies
```

## Basic Usage

```python
from market_data import get_prices

# Fetch price data
data = get_prices("AAPL", "2024-01-01", "2024-12-31")

# Access the DataFrame
print(data.df.head())
#             Open    High     Low   Close    Volume  Adj_Open  ...
# 2024-01-02  185.5  186.74  184.10  185.64  82488700    185.5  ...
# 2024-01-03  184.3  185.88  183.43  184.25  58414500    184.3  ...

# Check metadata
print(f"Ticker: {data.ticker}")
print(f"Provider: {data.provider}")
print(f"Rows from cache: {data.from_cache}")
print(f"Rows from API: {data.from_api}")
```

## Common Patterns

### Explicit Provider Selection

```python
from market_data import get_prices, Provider

# Use Tiingo explicitly
data = get_prices("SPY", "2024-01-01", "2024-01-31",
                  provider=Provider.TIINGO)

# Use Barchart explicitly (requires cookies)
data = get_prices("SPY", "2024-01-01", "2024-01-31",
                  provider=Provider.BARCHART)

# Auto-select (Barchart first, Tiingo fallback)
data = get_prices("SPY", "2024-01-01", "2024-01-31",
                  provider=Provider.AUTO)
```

### Force Refresh (Bypass Cache)

```python
# Always fetch fresh data from provider
data = get_prices("MSFT", "2024-06-01", "2024-06-30",
                  refresh=True)
```

### Access Adjusted vs Unadjusted Prices

```python
data = get_prices("AAPL", "2024-01-01", "2024-06-30")

# Unadjusted prices (raw)
unadj = data.df[["Open", "High", "Low", "Close", "Volume"]]

# Adjusted prices (for returns/analysis)
adj = data.df[["Adj_Open", "Adj_High", "Adj_Low", "Adj_Close", "Adj_Volume"]]
```

### Error Handling

```python
from market_data import (
    get_prices,
    ConfigurationError,
    ProviderError,
    CacheError,
)

try:
    data = get_prices("AAPL", "2024-01-01", "2024-12-31")
except ConfigurationError as e:
    print(f"Missing credential: {e.credential_name}")
    print(f"Expected at: {e.expected_location}")
except ProviderError as e:
    print(f"Provider {e.provider} failed: {e}")
    print(f"HTTP status: {e.status_code}")
except CacheError as e:
    print(f"Cache operation '{e.operation}' failed: {e}")
```

## Verification Commands

### Check Cache Contents

```bash
sqlite3 ~/.config/market-data/prices.db \
  "SELECT ticker, COUNT(*), MIN(date), MAX(date) FROM prices GROUP BY ticker"
```

### Check Credential Files

```bash
# List config files
ls -la ~/.config/market-data/

# Verify credentials.json (don't expose API key)
python -c "import json; print(json.load(open('~/.config/market-data/credentials.json'.replace('~', '$HOME'))).keys())"

# Check cookie freshness
python -c "
import json
from datetime import datetime
data = json.load(open('~/.config/market-data/barchart_cookies.json'.replace('~', '$HOME')))
captured = datetime.fromisoformat(data['captured_at'].replace('Z', '+00:00'))
print(f'Cookies captured: {captured}')
"
```

### Test API Connection

```python
# Quick test with minimal data
from market_data import get_prices

data = get_prices("SPY", "2024-01-02", "2024-01-05")
assert len(data.df) > 0, "No data returned"
assert "Close" in data.df.columns, "Missing Close column"
assert "Adj_Close" in data.df.columns, "Missing Adj_Close column"
print("API connection verified!")
```

## Cookie Refresh (Barchart Only)

Barchart cookies expire. Set up automatic refresh:

### Manual Refresh

```bash
python -m market_data.refresh.capture_cookies
```

### Automatic Refresh (macOS)

```bash
# Copy launchd plist
cp launchd/com.market-data.barchart-refresh.plist ~/Library/LaunchAgents/

# Load the schedule (runs every 4 hours)
launchctl load ~/Library/LaunchAgents/com.market-data.barchart-refresh.plist

# Check status
launchctl list | grep market-data
```

## Troubleshooting

### "ConfigurationError: Missing tiingo_api_key"

```bash
# Ensure credentials.json exists and has the key
cat ~/.config/market-data/credentials.json
```

### "ProviderError: 401 Unauthorized" (Barchart)

```bash
# Refresh cookies
python -m market_data.refresh.capture_cookies
```

### "CacheError: database is locked"

```bash
# Ensure no other process is accessing the cache
lsof ~/.config/market-data/prices.db

# If stuck, delete and recreate
rm ~/.config/market-data/prices.db
```

### Slow First Request

First request for a ticker fetches from API. Subsequent requests use cache:

```python
# First call: fetches from API (slow)
data1 = get_prices("AAPL", "2024-01-01", "2024-12-31")
print(f"From API: {data1.from_api}")  # e.g., 252

# Second call: uses cache (fast)
data2 = get_prices("AAPL", "2024-01-01", "2024-12-31")
print(f"From cache: {data2.from_cache}")  # e.g., 252
```
