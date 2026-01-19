# Centralized Market Data API - Implementation Plan

## Overview

Create a **brand new standalone project** for:
1. Centralized credential storage at `~/.config/market-data/`
2. **SQLite database caching** - check DB first, only fetch missing data
3. Automatic Barchart cookie refresh every 4 hours
4. Simple unified API: `get_prices(ticker, start, end, frequency, provider)` → DataFrame with adjusted + unadjusted OHLCV

---

## Architecture

```
/Users/ravivedula/Library/CloudStorage/Dropbox/1-projects/market-data-api/
├── pyproject.toml
├── PLAN.md
├── market_data/
│   ├── __init__.py           # Exports: get_prices, Frequency, Provider
│   ├── api.py                # Main get_prices() function
│   ├── credentials.py        # Load from ~/.config/market-data/
│   ├── cache/
│   │   ├── __init__.py
│   │   └── database.py       # SQLite cache layer
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract provider interface
│   │   ├── barchart.py       # Barchart: 2 queries (dividends=true/false)
│   │   └── tiingo.py         # Tiingo provider
│   └── refresh/
│       ├── __init__.py
│       └── capture_cookies.py  # Playwright cookie capture
├── scripts/
│   └── refresh-barchart-cookies  # Shell script for launchd
└── launchd/
    └── com.market-data.barchart-refresh.plist

~/.config/market-data/
├── credentials.json          # API keys, Barchart username
├── barchart_cookies.json     # Auto-refreshed every 4 hours
├── prices.db                 # SQLite price cache database
└── logs/                     # Refresh logs
```

---

## SQLite Cache Database

**Location**: `~/.config/market-data/prices.db`

**Schema**:
```sql
CREATE TABLE prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    frequency TEXT NOT NULL,      -- 'daily', 'weekly', 'monthly'
    provider TEXT NOT NULL,       -- 'barchart', 'tiingo'
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    adj_open REAL,
    adj_high REAL,
    adj_low REAL,
    adj_close REAL,
    adj_volume REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date, frequency, provider)
);

CREATE INDEX idx_ticker_date ON prices(ticker, date);
CREATE INDEX idx_ticker_frequency ON prices(ticker, frequency);
```

---

## Cache-First Data Flow

```
get_prices("AAPL", "2024-01-01", "2024-12-31")
                │
                ▼
┌─────────────────────────────────────────┐
│ 1. Query SQLite for existing data       │
│    SELECT * FROM prices                 │
│    WHERE ticker='AAPL'                  │
│    AND date BETWEEN '2024-01-01'        │
│                  AND '2024-12-31'       │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 2. Identify missing date ranges         │
│    - Has: 2024-01-01 to 2024-06-30     │
│    - Missing: 2024-07-01 to 2024-12-31 │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 3. Fetch ONLY missing data from API     │
│    - Barchart: dividends=false          │
│    - Barchart: dividends=true           │
│    (no delay between same ticker)       │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 4. Insert new data into SQLite          │
│    INSERT OR REPLACE INTO prices...     │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 5. Return combined DataFrame            │
│    (cached + newly fetched)             │
└─────────────────────────────────────────┘
```

---

## API Design

```python
from market_data import get_prices, Frequency, Provider

# Simple usage - checks cache first, fetches missing data only
df = get_prices("AAPL", "2024-01-01", "2024-12-31").df

# Full API
data = get_prices(
    ticker="AAPL",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency=Frequency.DAILY,      # DAILY | WEEKLY | MONTHLY
    provider=Provider.AUTO,         # AUTO | TIINGO | BARCHART
    refresh=False                   # True = bypass cache, refetch all
)

# Returns PriceData with:
# - data.df: DataFrame with columns:
#   Date (index), Open, High, Low, Close, Volume,
#   Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume
# - data.provider: str ("tiingo" or "barchart")
# - data.ticker: str
# - data.from_cache: int (number of rows from cache)
# - data.from_api: int (number of rows fetched from API)
```

---

## Cache Module

```python
# market_data/cache/database.py

class PriceCache:
    def __init__(self, db_path="~/.config/market-data/prices.db"):
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def get_cached_data(self, ticker, start_date, end_date, frequency, provider):
        """Return cached data and identify missing date ranges."""
        # Returns: (cached_df, missing_ranges)
        # missing_ranges: [(start1, end1), (start2, end2), ...]

    def get_missing_ranges(self, ticker, start_date, end_date, frequency, provider):
        """Identify gaps in cached data."""
        # Returns list of (start, end) tuples for missing periods

    def save_prices(self, ticker, df, frequency, provider):
        """Insert or update price data in cache."""
        # Uses INSERT OR REPLACE to handle duplicates

    def get_last_date(self, ticker, frequency, provider):
        """Get most recent cached date for a ticker."""
        # Useful for incremental updates
```

---

## Barchart Implementation

**Two API calls per ticker (no delay between them):**

1. **Unadjusted prices**: `dividends=false`
   - Returns: Open, High, Low, Close, Volume

2. **Adjusted prices**: `dividends=true`
   - Returns: Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume

**Only fetches missing date ranges from cache analysis.**

```python
# Pseudocode
missing_ranges = cache.get_missing_ranges(ticker, start, end)

for range_start, range_end in missing_ranges:
    unadj_df = fetch_barchart(ticker, range_start, range_end, dividends=False)
    adj_df = fetch_barchart(ticker, range_start, range_end, dividends=True)

    # Merge and save to cache
    merged = unadj_df.join(adj_df)
    cache.save_prices(ticker, merged, frequency, provider)
```

---

## Rate Limiting Strategy

| Scenario | Delay |
|----------|-------|
| Between 2 requests for same ticker (adj/unadj) | **0 seconds** |
| Between different tickers | **2 seconds** |
| After every 10 tickers | **30 seconds** |

```python
class RateLimiter:
    def __init__(self):
        self.ticker_count = 0

    def wait_for_next_ticker(self):
        self.ticker_count += 1
        if self.ticker_count % 10 == 0:
            time.sleep(30)  # 30 sec pause every 10 tickers
        else:
            time.sleep(2)   # 2 sec between tickers
```

---

## Credential Storage

**~/.config/market-data/credentials.json:**
```json
{
  "tiingo_api_key": "your-tiingo-key",
  "barchart_username": "email@example.com",
  "barchart_password_env": "BARCHART_PASSWORD"
}
```

**~/.config/market-data/barchart_cookies.json:**
```json
{
  "cookie_string": "...",
  "xsrf_token": "...",
  "user_agent": "...",
  "captured_at": "2026-01-18T16:20:05Z"
}
```

Password stays in `~/.zshrc` as `export BARCHART_PASSWORD="..."`.

---

## Implementation Steps

### Phase 1: Project Setup
1. Create project directory structure
2. Create `pyproject.toml` with dependencies
3. Create `~/.config/market-data/` directory and credential files

### Phase 2: SQLite Cache Layer
1. Implement `cache/database.py` with PriceCache class
2. Create database schema with proper indexes
3. Implement `get_missing_ranges()` for gap detection
4. Implement `save_prices()` with INSERT OR REPLACE

### Phase 3: Credential Management
1. Implement `credentials.py` - load API keys and cookies from central location
2. Implement `capture_cookies.py` - Playwright-based Barchart cookie capture
3. Write cookies to `~/.config/market-data/barchart_cookies.json`

### Phase 4: Providers
1. Implement `barchart.py`:
   - Cookie-based authentication
   - Two queries: `dividends=true` and `dividends=false` (no delay between)
   - Merge into single DataFrame with Adj_* columns
   - Rate limiting: 2s between tickers, 30s every 10 tickers
   - **Only fetch missing date ranges**
2. Implement `tiingo.py`:
   - API key authentication
   - Returns both adjusted and unadjusted in one call

### Phase 5: Unified API
1. Implement `api.py` with `get_prices()` function
2. Cache-first logic: check DB → identify gaps → fetch missing → merge
3. Provider auto-selection (Tiingo preferred, Barchart fallback)
4. Consistent DataFrame output format

### Phase 6: Cookie Refresh Automation
1. Create launchd plist for 4-hour refresh schedule
2. Create shell wrapper script
3. Install and load launchd service

### Phase 7: Installation & Testing
1. Install package: `pip install -e .`
2. Test cache hit/miss scenarios
3. Test from multiple directories

---

## Files to Create

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package configuration |
| `market_data/__init__.py` | Package exports |
| `market_data/api.py` | Main `get_prices()` function |
| `market_data/credentials.py` | Central credential loader |
| `market_data/cache/__init__.py` | Cache module init |
| `market_data/cache/database.py` | SQLite cache layer |
| `market_data/providers/base.py` | Abstract provider interface |
| `market_data/providers/barchart.py` | Barchart (2 queries, merged) |
| `market_data/providers/tiingo.py` | Tiingo provider |
| `market_data/refresh/capture_cookies.py` | Cookie capture script |
| `scripts/refresh-barchart-cookies` | Shell wrapper for launchd |
| `launchd/com.market-data.barchart-refresh.plist` | 4-hour schedule |
| `~/.config/market-data/credentials.json` | API keys |
| `~/.config/market-data/barchart_cookies.json` | Session cookies |
| `~/.config/market-data/prices.db` | SQLite price cache |

---

## Verification

1. Test API from Python (first call fetches, second uses cache):
   ```bash
   # First call - fetches from API
   python -c "from market_data import get_prices; d = get_prices('SPY', '2024-01-01', '2024-01-10'); print(f'Cache: {d.from_cache}, API: {d.from_api}')"

   # Second call - should be 100% cache
   python -c "from market_data import get_prices; d = get_prices('SPY', '2024-01-01', '2024-01-10'); print(f'Cache: {d.from_cache}, API: {d.from_api}')"
   ```

2. Check database has data:
   ```bash
   sqlite3 ~/.config/market-data/prices.db "SELECT ticker, COUNT(*) FROM prices GROUP BY ticker"
   ```

3. Check cookies are fresh:
   ```bash
   cat ~/.config/market-data/barchart_cookies.json | python -m json.tool
   ```

4. Verify launchd service:
   ```bash
   launchctl list | grep market-data
   ```

---

## Dependencies

- `pandas` - DataFrame handling
- `requests` - HTTP requests
- `playwright` - Browser automation for cookie capture
- `playwright-stealth` - Anti-detection for Playwright
- (SQLite is built into Python - no extra dependency)
