# Research: Market Data API Library

**Feature**: 001-market-data-api
**Date**: 2026-01-19

## Overview

This document consolidates technical decisions for the Market Data API library. Most decisions are pre-established in `PLAN-v3-reuse-existing-code.md` as the authoritative source. This research validates those decisions and documents rationale.

---

## Decision 1: Code Reuse Strategy

**Decision**: Copy and refactor existing `ffn` package code rather than writing from scratch.

**Rationale**:
- Existing code is already debugged and working in production
- Reduces implementation time by ~80%
- Preserves battle-tested HTTP handling, CSV parsing, and rate limiting logic
- Removes tight coupling to `ffn` package internals

**Alternatives Considered**:
- Write from scratch: Rejected - unnecessary risk of introducing bugs in working code
- Import `ffn` as dependency: Rejected - violates FR-016 (no ffn dependencies)
- Fork `ffn` repo: Rejected - too heavy; only need specific modules

**Source Mapping** (from PLAN-v3):
| Target | Source | Reuse % |
|--------|--------|---------|
| `providers/barchart.py` | `ffn/barchart_provider.py` | 95% |
| `providers/tiingo.py` | `ffn/tiingo_provider.py` | 95% |
| `credentials.py` | `ffn/barchart_cookies.py` | 70% |
| `refresh/capture_cookies.py` | `ffn/capture_cookies_cdp.py` | 90% |

---

## Decision 2: Caching Strategy

**Decision**: SQLite database with cache-first lookup and intelligent gap-filling.

**Rationale**:
- SQLite is built into Python - no additional dependencies
- Supports atomic transactions for data integrity
- SQL queries efficiently identify missing date ranges
- File-based storage survives process restarts
- Single-user access pattern fits SQLite's concurrency model

**Alternatives Considered**:
- In-memory cache (dict): Rejected - data lost on restart; no persistence
- Redis: Rejected - requires external service; overkill for single-user library
- Parquet files: Rejected - harder to query for missing ranges; more complex gap detection
- PostgreSQL: Rejected - requires server setup; inappropriate for library

**Schema** (from PLAN-v3):
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

---

## Decision 3: Credential Storage Location

**Decision**: Store all credentials in `~/.config/market-data/` as JSON files.

**Rationale**:
- Follows XDG Base Directory specification for config files
- Centralized location for all credential types
- JSON format is human-readable and easy to validate
- Separate files for different credential types (credentials.json vs barchart_cookies.json)
- User home directory ensures credentials aren't committed to repos

**Alternatives Considered**:
- Environment variables: Rejected - harder to manage; doesn't persist across sessions
- `.env` file in project: Rejected - risk of committing to version control
- macOS Keychain: Rejected - platform-specific; harder to automate refresh
- Encrypted file: Rejected - adds complexity; file permissions sufficient for single-user

**File Structure**:
```
~/.config/market-data/
├── credentials.json          # Tiingo API key, Barchart username
├── barchart_cookies.json     # Auto-refreshed browser cookies
├── prices.db                 # SQLite cache
└── logs/                     # Refresh script logs
```

---

## Decision 4: Rate Limiting Implementation

**Decision**: Provider-specific rate limiting with internal enforcement.

**Rationale**:
- Different providers have different rate limits
- Internal enforcement prevents user errors
- Rate limiter state persists across calls in same session
- Sleep-based delays are simple and reliable

**Barchart Rate Limits** (from PLAN-v3):
| Scenario | Delay |
|----------|-------|
| Between adj/unadj for same ticker | 0 seconds |
| Between different tickers | 2 seconds |
| After every 10 tickers | 30 seconds |

**Tiingo Rate Limits**:
- Varies by subscription tier
- Free tier: 500 requests/day, 50 requests/hour
- Implementation: Track request counts; raise warning when approaching limits

**Alternatives Considered**:
- User-configurable delays: Rejected - adds complexity; users may set incorrectly
- Token bucket algorithm: Rejected - overkill for simple sequential requests
- No rate limiting (rely on provider 429s): Rejected - risks account suspension

---

## Decision 5: Provider AUTO Mode Priority

**Decision**: Barchart first (if cookies valid), Tiingo as fallback.

**Rationale**:
- Barchart provides both adjusted and unadjusted prices directly (2 queries)
- Barchart has more generous rate limits for authenticated users
- Tiingo free tier has stricter daily limits
- Cookie validity can be checked before attempting request

**Implementation**:
```python
if provider == Provider.AUTO:
    if barchart_cookies_valid():
        try:
            return fetch_from_barchart(...)
        except ProviderError:
            pass  # Fall through to Tiingo
    return fetch_from_tiingo(...)
```

**Alternatives Considered**:
- Tiingo first: Rejected - stricter rate limits on free tier
- Parallel fetch: Rejected - wastes API calls; unnecessary complexity
- User preference config: Rejected - adds configuration burden

---

## Decision 6: Exception Hierarchy

**Decision**: Custom exception hierarchy with base `MarketDataError`.

**Rationale**:
- Enables selective exception handling
- Clear categorization: configuration vs provider vs cache issues
- Actionable error messages with recovery hints
- Follows Python best practices for library exceptions

**Hierarchy**:
```
MarketDataError (base)
├── ConfigurationError   # Missing credentials, invalid config
├── ProviderError        # HTTP errors, invalid responses
└── CacheError           # SQLite corruption, write failures
```

**Alternatives Considered**:
- Use built-in exceptions only: Rejected - less informative; harder to catch library-specific errors
- Single exception type: Rejected - can't distinguish error categories
- Third-party exception library: Rejected - unnecessary dependency

---

## Decision 7: Package Structure

**Decision**: Single package `market_data` with submodules.

**Rationale**:
- Flat public API (`from market_data import get_prices`)
- Internal modules hidden from consumers
- Follows Python packaging conventions
- Easy to install with `pip install`

**Public Exports** (`__init__.py`):
- `get_prices` - main function
- `Frequency` - enum (DAILY only initially)
- `Provider` - enum (BARCHART, TIINGO, AUTO)
- `PriceData` - result dataclass
- Exception classes

**Alternatives Considered**:
- Multiple packages: Rejected - unnecessary for this scope
- Namespace package: Rejected - adds complexity without benefit
- Single module (no subpackages): Rejected - poor organization for 10+ files

---

## Decision 8: Testing Strategy

**Decision**: pytest with mocked providers for unit tests; real providers for integration tests.

**Rationale**:
- Unit tests must be deterministic and fast (no network calls)
- Integration tests verify real provider behavior with known tickers
- pytest-mock provides clean mocking interface
- Separate test directories for unit vs integration

**Test Coverage Requirements**:
- Unit: 90%+ coverage on business logic
- Integration: Happy path for each provider

**Alternatives Considered**:
- VCR/cassette recording: Rejected - stale recordings may drift from real API
- Contract tests only: Rejected - insufficient for catching logic bugs
- No integration tests: Rejected - must verify real provider behavior

---

## Open Questions (None)

All technical decisions have been made. No NEEDS CLARIFICATION items remain.

---

## References

- `PLAN-v3-reuse-existing-code.md` - Authoritative source for code mapping and architecture
- `.specify/memory/constitution.md` - Governance principles
- `specs/001-market-data-api/spec.md` - Feature specification
