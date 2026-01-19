# Centralized Market Data API - Implementation Plan v3

## Overview

Create a **self-contained, independent package** by:
1. **Copy** existing working code to the new location
2. **Refactor** to remove ALL ffn dependencies
3. Package is **completely standalone** - no imports from ffn

**Source files to copy and refactor:**
- `ffn/barchart_provider.py` → `providers/barchart.py`
- `ffn/barchart_cookies.py` → `credentials.py`
- `ffn/capture_cookies_cdp.py` → `refresh/capture_cookies.py`
- `ffn/tiingo_provider.py` → `providers/tiingo.py`
- `etf_price_capture.py` → patterns for `api.py`

**Key principle**: Copy debugged code, refactor to be independent.

---

## Source Code Mapping (Copy + Refactor)

| New Package File | Copy From | Refactor Changes |
|------------------|-----------|------------------|
| `providers/barchart.py` | `ffn/barchart_provider.py` | Remove `from . import utils`, `from .barchart_cookies import`, use local credentials module |
| `providers/tiingo.py` | `ffn/tiingo_provider.py` | Remove `from . import utils`, use local credentials module |
| `credentials.py` | `ffn/barchart_cookies.py` | Change to read JSON from `~/.config/market-data/` instead of env vars |
| `refresh/capture_cookies.py` | `ffn/capture_cookies_cdp.py` | Change output from `.env` to `~/.config/market-data/barchart_cookies.json` |
| `cache/database.py` | **New code** | SQLite caching layer |
| `api.py` | Pattern from `etf_price_capture.py` | Simplified `get_prices()` API with cache-first logic |

---

## Code Reuse Details (Copy These Functions)

### From `ffn/barchart_provider.py` → Copy to `providers/barchart.py`
**Copy these functions as-is:**
- `_validate_ticker()` - ticker validation (lines 62-84)
- `_get_barchart_session()` - HTTP session with retry (lines 90-120)
- `_format_barchart_date()` - date formatting (lines 123-152)
- `_normalize_interval()` - interval params (lines 155-181)
- `_build_headers()` - HTTP headers (lines 184-211)
- `_build_params()` - query params (lines 214-258)
- `_parse_barchart_csv()` - CSV parsing (lines 261-320)
- `_execute_request()` - HTTP request (lines 323-353)
- `_perform_fetch()` - fetch execution (lines 392-436)

**Copy and modify:**
- `_prepare_cookie_bundle()` - change to load from `~/.config/market-data/barchart_cookies.json` instead of env vars

**Remove (don't copy):**
- `from . import utils` import
- `from .barchart_cookies import get_barchart_cookies` import
- `@utils.memoize` decorator (use `@lru_cache` instead)

### From `ffn/tiingo_provider.py` → Copy to `providers/tiingo.py`
**Copy these functions as-is:**
- `_get_tiingo_session()` - HTTP session (lines 83-103)
- `_validate_ticker()` - ticker validation (lines 124-148)
- `_format_iso_date()` - date formatting (lines 151-171)
- `_build_tiingo_params()` - query params (lines 196-216)
- `_perform_tiingo_request()` - HTTP request (lines 219-319)
- `_rows_to_tiingo_dataframe()` - response parsing (lines 322-398)

**Copy and modify:**
- `_resolve_tiingo_api_key()` - load from `~/.config/market-data/credentials.json` instead of env var

**Remove (don't copy):**
- `from . import utils` import

### From `ffn/capture_cookies_cdp.py` → Copy to `refresh/capture_cookies.py`
**Copy these functions as-is:**
- `login()` - login flow (lines 106-178)
- `main()` - cookie capture flow (lines 180-277)

**Copy and modify:**
- `update_env_file()` → rename to `save_cookies_json()` - write JSON to `~/.config/market-data/barchart_cookies.json` instead of `.env`

### From `etf_price_capture.py` → Use patterns for `api.py`
**Copy and adapt these patterns:**
- `RateLimiter` class (lines 35-67) - adapt for new rate limits
- `FetchResult` dataclass pattern (lines 84-94)
- `fetch_barchart_data()` logic (lines 179-229) - 2 queries for adj/unadj

---

## Rate Limiting (Updated)

```python
class RateLimiter:
    """Rate limiter with ticker-based delays."""

    def __init__(self):
        self.ticker_count = 0
        self.last_ticker_time: Optional[float] = None

    def wait_between_tickers(self):
        """Wait between different tickers (not between same ticker adj/unadj)."""
        self.ticker_count += 1

        if self.ticker_count % 10 == 0:
            # 30 second pause every 10 tickers
            time.sleep(30)
        else:
            # 2 second delay between tickers
            if self.last_ticker_time:
                elapsed = time.time() - self.last_ticker_time
                if elapsed < 2:
                    time.sleep(2 - elapsed)

        self.last_ticker_time = time.time()
```

| Scenario | Delay |
|----------|-------|
| Between adj/unadj for same ticker | **0 seconds** |
| Between different tickers | **2 seconds** |
| After every 10 tickers | **30 seconds** |

---

## Architecture

```
/Users/ravivedula/Library/CloudStorage/Dropbox/1-projects/market-data-api/
├── pyproject.toml
├── PLAN-v3-reuse-existing-code.md
├── market_data/
│   ├── __init__.py           # Exports: get_prices, Frequency, Provider
│   ├── api.py                # Main get_prices() - adapted from etf_price_capture.py
│   ├── credentials.py        # Load from ~/.config/market-data/
│   ├── cache/
│   │   ├── __init__.py
│   │   └── database.py       # SQLite cache layer (NEW)
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── barchart.py       # Adapted from ffn/barchart_provider.py
│   │   └── tiingo.py         # Adapted from ffn/tiingo_provider.py
│   └── refresh/
│       ├── __init__.py
│       └── capture_cookies.py  # Adapted from ffn/capture_cookies_cdp.py
├── scripts/
│   └── refresh-barchart-cookies
└── launchd/
    └── com.market-data.barchart-refresh.plist

~/.config/market-data/
├── credentials.json          # {"tiingo_api_key": "...", "barchart_username": "..."}
├── barchart_cookies.json     # Auto-refreshed every 4 hours
├── prices.db                 # SQLite cache
└── logs/
```

---

## SQLite Cache (NEW)

**Schema** (adapted from price_capture_config.py patterns):
```sql
CREATE TABLE prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    frequency TEXT NOT NULL,
    provider TEXT NOT NULL,
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
```

**Cache-First Flow:**
1. Query SQLite for existing data
2. Identify missing date ranges
3. Fetch ONLY missing data (2 Barchart queries: adj + unadj, no delay between)
4. Insert into SQLite
5. Return combined DataFrame

---

## API Design

```python
from market_data import get_prices, Frequency, Provider

# Simple usage
df = get_prices("AAPL", "2024-01-01", "2024-12-31").df

# Full API
data = get_prices(
    ticker="AAPL",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency=Frequency.DAILY,
    provider=Provider.BARCHART,  # or TIINGO, AUTO
    refresh=False                # True = bypass cache
)

# Returns PriceData:
# - data.df: DataFrame with Open, High, Low, Close, Volume, Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume
# - data.ticker: str
# - data.provider: str
# - data.from_cache: int
# - data.from_api: int
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

---

## Implementation Steps

### Phase 1: Project Setup
1. Create directory structure
2. Create `pyproject.toml`
3. Create `~/.config/market-data/` with template files

### Phase 2: Adapt Providers (reuse existing code)
1. Copy `barchart_provider.py` → `providers/barchart.py`
   - Remove `from . import utils` and `from .barchart_cookies import`
   - Update `_prepare_cookie_bundle()` to read from JSON file
2. Copy `tiingo_provider.py` → `providers/tiingo.py`
   - Remove `from . import utils`
   - Update `_resolve_tiingo_api_key()` to read from JSON file

### Phase 3: Adapt Cookie Capture (reuse existing code)
1. Copy `capture_cookies_cdp.py` → `refresh/capture_cookies.py`
   - Update `update_env_file()` to write JSON to `~/.config/market-data/barchart_cookies.json`

### Phase 4: SQLite Cache (new code)
1. Implement `cache/database.py` with PriceCache class
2. Methods: `get_cached_data()`, `get_missing_ranges()`, `save_prices()`

### Phase 5: Unified API
1. Create `api.py` with `get_prices()` function
2. Implement cache-first logic
3. Adapt `fetch_barchart_data()` pattern from `etf_price_capture.py`

### Phase 6: Cookie Refresh Automation
1. Create launchd plist (every 4 hours)
2. Create shell wrapper script

### Phase 7: Install & Test
1. `pip install -e .`
2. Test cache hit/miss scenarios

---

## Files to Create

| File | Source | Notes |
|------|--------|-------|
| `pyproject.toml` | New | Package config |
| `market_data/__init__.py` | New | Exports |
| `market_data/api.py` | Adapt `etf_price_capture.py` | Main API |
| `market_data/credentials.py` | Adapt `barchart_cookies.py` | Central loader |
| `market_data/cache/database.py` | New | SQLite cache |
| `market_data/providers/barchart.py` | Adapt `barchart_provider.py` | 95% reuse |
| `market_data/providers/tiingo.py` | Adapt `tiingo_provider.py` | 95% reuse |
| `market_data/refresh/capture_cookies.py` | Adapt `capture_cookies_cdp.py` | 90% reuse |

---

## Key Differences from ffn

| Aspect | ffn | market_data (new standalone package) |
|--------|-----|--------------------------------------|
| Dependencies | Has internal module deps | **Completely self-contained, no ffn imports** |
| Credentials | `.env` in project dir | `~/.config/market-data/` JSON files |
| Caching | None | SQLite database |
| API | Returns Series by default | Returns DataFrame with adj+unadj |
| Barchart queries | 1 query | 2 queries (adj + unadj) |
| Rate limiting | 20s all requests | 0s same ticker, 2s between, 30s/10 |
| Installation | Part of ffn package | Independent `pip install -e .` |

---

## Verification

1. Test API:
   ```bash
   python -c "from market_data import get_prices; print(get_prices('SPY', '2024-01-01', '2024-01-10').df)"
   ```

2. Check cache:
   ```bash
   sqlite3 ~/.config/market-data/prices.db "SELECT ticker, COUNT(*) FROM prices GROUP BY ticker"
   ```

3. Check cookies:
   ```bash
   cat ~/.config/market-data/barchart_cookies.json | python -m json.tool
   ```

---

## Dependencies

- `pandas` - DataFrame handling
- `requests` - HTTP requests
- `playwright` - Browser automation
- `playwright-stealth` - Anti-detection
- (SQLite built into Python)
