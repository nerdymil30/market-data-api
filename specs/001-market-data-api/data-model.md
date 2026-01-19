# Data Model: Market Data API Library

**Feature**: 001-market-data-api
**Date**: 2026-01-19

## Overview

This document defines the data entities, their attributes, relationships, and validation rules for the Market Data API library.

---

## Entities

### 1. PriceData

**Description**: The result object returned by `get_prices()`. Contains the price DataFrame plus metadata about the fetch operation.

**Attributes**:

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `df` | `pandas.DataFrame` | Price data with OHLCV columns | See DataFrame Schema below |
| `ticker` | `str` | The requested ticker symbol | Uppercase, 1-10 chars |
| `provider` | `str` | Data source ("barchart" or "tiingo") | Enum value |
| `from_cache` | `int` | Number of rows retrieved from cache | >= 0 |
| `from_api` | `int` | Number of rows fetched from provider API | >= 0 |
| `start_date` | `date` | Requested start date | ISO format |
| `end_date` | `date` | Requested end date | ISO format |

**DataFrame Schema** (`PriceData.df`):

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| Index | `DatetimeIndex` | Trading date | Date only, no time |
| `Open` | `float64` | Unadjusted opening price | >= 0, 4 decimal precision |
| `High` | `float64` | Unadjusted daily high | >= Open, >= Low |
| `Low` | `float64` | Unadjusted daily low | <= Open, <= High |
| `Close` | `float64` | Unadjusted closing price | >= 0, 4 decimal precision |
| `Volume` | `int64` | Trading volume | >= 0 |
| `Adj_Open` | `float64` | Split/dividend adjusted open | >= 0 |
| `Adj_High` | `float64` | Split/dividend adjusted high | >= 0 |
| `Adj_Low` | `float64` | Split/dividend adjusted low | >= 0 |
| `Adj_Close` | `float64` | Split/dividend adjusted close | >= 0 |
| `Adj_Volume` | `int64` | Adjusted volume | >= 0 |

**Invariants**:
- `from_cache + from_api == len(df)` (total rows equals cache + API contributions)
- DataFrame is sorted by date ascending
- No duplicate dates in index
- Missing data represented as `NaN`, not filled or interpolated

---

### 2. PriceRecord (Cache Row)

**Description**: A single row of cached price data in the SQLite database.

**Attributes**:

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `ticker` | `TEXT` | Stock ticker symbol | NOT NULL, uppercase |
| `date` | `DATE` | Trading date | NOT NULL, ISO format |
| `frequency` | `TEXT` | Data frequency | NOT NULL, "daily" |
| `provider` | `TEXT` | Data source | NOT NULL, "barchart" or "tiingo" |
| `open` | `REAL` | Unadjusted open | Nullable |
| `high` | `REAL` | Unadjusted high | Nullable |
| `low` | `REAL` | Unadjusted low | Nullable |
| `close` | `REAL` | Unadjusted close | Nullable |
| `volume` | `REAL` | Volume | Nullable (stored as REAL for SQLite) |
| `adj_open` | `REAL` | Adjusted open | Nullable |
| `adj_high` | `REAL` | Adjusted high | Nullable |
| `adj_low` | `REAL` | Adjusted low | Nullable |
| `adj_close` | `REAL` | Adjusted close | Nullable |
| `adj_volume` | `REAL` | Adjusted volume | Nullable |
| `fetched_at` | `TIMESTAMP` | When data was fetched | DEFAULT CURRENT_TIMESTAMP |

**Primary Key**: `(ticker, date, frequency, provider)`

**Indexes**:
- Primary key index (implicit)
- Consider index on `(ticker, date)` for common query pattern

---

### 3. Credentials

**Description**: Authentication configuration for data providers.

**File**: `~/.config/market-data/credentials.json`

**Schema**:
```json
{
  "tiingo_api_key": "string",
  "barchart_username": "string",
  "barchart_password_env": "string"
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `tiingo_api_key` | `string` | Tiingo API token | For Tiingo provider |
| `barchart_username` | `string` | Barchart login email | For cookie refresh |
| `barchart_password_env` | `string` | Env var name containing password | For cookie refresh |

**Validation**:
- File must exist and be valid JSON
- At least one provider's credentials must be present
- Missing required field raises `ConfigurationError`

---

### 4. BarchartCookies

**Description**: Browser session cookies for Barchart authentication.

**File**: `~/.config/market-data/barchart_cookies.json`

**Schema**:
```json
{
  "cookie_string": "string",
  "xsrf_token": "string",
  "user_agent": "string",
  "captured_at": "ISO8601 timestamp"
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `cookie_string` | `string` | Full cookie header value | Yes |
| `xsrf_token` | `string` | CSRF token for requests | Yes |
| `user_agent` | `string` | Browser user agent string | Yes |
| `captured_at` | `string` | ISO 8601 timestamp of capture | Yes |

**Validation**:
- All fields required
- `captured_at` should be within last 24 hours (warning if older)
- Cookie validity checked by attempting lightweight request

---

## Enums

### Frequency

```python
class Frequency(Enum):
    DAILY = "daily"
    # Future: WEEKLY, MONTHLY, INTRADAY
```

### Provider

```python
class Provider(Enum):
    BARCHART = "barchart"
    TIINGO = "tiingo"
    AUTO = "auto"
```

---

## Relationships

```
┌─────────────┐       returns        ┌─────────────┐
│ get_prices()│ ──────────────────── │  PriceData  │
└─────────────┘                      └─────────────┘
       │                                    │
       │ uses                               │ contains
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│ PriceCache  │ ◄─────────────────── │  DataFrame  │
└─────────────┘      stores/reads    └─────────────┘
       │
       │ persists
       ▼
┌─────────────┐
│ PriceRecord │  (SQLite row)
└─────────────┘
```

---

## State Transitions

### PriceData Lifecycle

```
Request → Cache Lookup → Gap Detection → API Fetch → Cache Write → Return
   │           │              │              │            │          │
   │           ▼              ▼              ▼            ▼          ▼
   │      [cache hit]    [missing       [fetch from   [atomic     [PriceData
   │      → partial       ranges]        provider]     insert]     object]
   │        data]
   │
   └─► [refresh=True] → Skip cache → Full API Fetch → Replace cache → Return
```

### Cookie Lifecycle

```
Fresh → Valid → Stale → Expired
  │       │       │        │
  │       │       │        └─► Refresh required (ProviderError)
  │       │       │
  │       │       └─► Warning logged; still usable
  │       │
  │       └─► Normal operation
  │
  └─► Just refreshed (captured_at < 4 hours)
```

---

## Validation Rules

### Ticker Validation
- Must be 1-10 uppercase alphanumeric characters
- No special characters except `.` and `-` (e.g., `BRK.B`, `BF-A`)
- Validated before any API call

### Date Validation
- Must be valid date in ISO format (YYYY-MM-DD) or Python date object
- `start_date` must be before `end_date`
- Dates in the future raise `ValueError`
- Dates before 1970-01-01 raise `ValueError`

### Price Validation (on storage)
- Prices must be >= 0 or NULL
- High >= Low (warning if violated, still stored)
- Volume must be >= 0 or NULL
