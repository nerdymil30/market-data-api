# PRD: Market Data API Library

## Introduction

Create a self-contained Python library (`market_data`) for fetching historical stock price data with intelligent caching. The library provides a simple `get_prices()` API that fetches OHLCV data (both adjusted and unadjusted) from Barchart or Tiingo, caches results in SQLite, and handles rate limiting automatically.

**Key Principle**: Reuse existing debugged code from the `ffn` package by copying and refactoring to remove dependencies, rather than writing from scratch.

**Problem Solved**: Currently, fetching market data requires dealing with multiple provider APIs, managing credentials, handling rate limits, and re-fetching the same data repeatedly. This library centralizes all of that into a single, cache-first API.

## Goals

- Provide a single `get_prices(ticker, start, end)` function that "just works"
- Cache all fetched data in SQLite to minimize API calls (80%+ reduction for repeated queries)
- Support both Barchart and Tiingo providers with automatic fallback
- Return both adjusted and unadjusted price data in every response
- Handle rate limiting internally (no user configuration needed)
- Automate Barchart cookie refresh via launchd (every 4 hours)
- Fail fast with clear, actionable error messages
- Achieve comprehensive test coverage (unit + integration + mocked providers)
- Design for reusability (installable via `uv pip install -e ".[dev]"` after `pyvenv`)
- Use `pyvenv` for transparent venv management (no manual activation needed)

## User Stories

### US-001: Project Setup and Package Structure
**Description:** As a developer, I need the package structure and configuration so I can install and import the library.

**Acceptance Criteria:**
- [ ] Create `pyproject.toml` with package metadata and dependencies (pandas, requests, playwright, playwright-stealth)
- [ ] Include dev dependencies in pyproject.toml: pytest, pytest-mock, pytest-cov, mypy, ruff
- [ ] Initialize project venv using `pyvenv` (creates and activates venv automatically)
- [ ] Install package in dev mode: `uv pip install -e ".[dev]"`
- [ ] Install Playwright browsers: `playwright install chromium`
- [ ] Create `market_data/__init__.py` exporting: `get_prices`, `Frequency`, `Provider`, `PriceData`
- [ ] Create `market_data/exceptions.py` with `MarketDataError`, `ConfigurationError`, `ProviderError`, `CacheError`
- [ ] `from market_data import get_prices` works after `pyvenv` activation
- [ ] Typecheck passes (`mypy market_data/`)
- [ ] Lint passes (`ruff check .`)

---

### US-002: Credentials Module
**Description:** As a user, I need credentials loaded from `~/.config/market-data/` so my API keys and cookies are stored securely outside the repo.

**Acceptance Criteria:**
- [ ] Create `market_data/credentials.py` adapted from `ffn/barchart_cookies.py`
- [ ] Load Tiingo API key from `~/.config/market-data/credentials.json`
- [ ] Load Barchart cookies from `~/.config/market-data/barchart_cookies.json`
- [ ] Raise `ConfigurationError` with file path if credentials file missing
- [ ] Raise `ConfigurationError` with field name if required field missing
- [ ] Never log or expose credential values in error messages
- [ ] Unit tests with mocked file system
- [ ] Typecheck passes

---

### US-003: Barchart Provider
**Description:** As a user, I want to fetch price data from Barchart so I can get both adjusted and unadjusted prices.

**Acceptance Criteria:**
- [ ] Create `market_data/providers/barchart.py` adapted from `ffn/barchart_provider.py`
- [ ] Remove all `ffn` imports (`from . import utils`, `from .barchart_cookies import`)
- [ ] Replace `@utils.memoize` with `@lru_cache`
- [ ] Load cookies via local `credentials.py` module
- [ ] Implement `fetch_prices(ticker, start, end, frequency)` returning DataFrame
- [ ] Fetch both adjusted AND unadjusted data (2 queries per ticker, 0s delay between)
- [ ] Validate ticker format before API call
- [ ] Raise `ProviderError` with HTTP status and response body on failure
- [ ] Retry with exponential backoff on 429/500/503 (max 3 attempts)
- [ ] Unit tests with mocked HTTP responses
- [ ] Integration test with real Barchart (known ticker, short date range)
- [ ] Typecheck passes

---

### US-004: Tiingo Provider
**Description:** As a user, I want to fetch price data from Tiingo as an alternative provider.

**Acceptance Criteria:**
- [ ] Create `market_data/providers/tiingo.py` adapted from `ffn/tiingo_provider.py`
- [ ] Remove all `ffn` imports
- [ ] Load API key via local `credentials.py` module
- [ ] Implement `fetch_prices(ticker, start, end, frequency)` returning DataFrame
- [ ] Return both adjusted and unadjusted columns (Tiingo provides adjusted by default)
- [ ] Validate ticker format before API call
- [ ] Raise `ProviderError` with HTTP status and response body on failure
- [ ] Retry with exponential backoff on 429/500/503 (max 3 attempts)
- [ ] Unit tests with mocked HTTP responses
- [ ] Integration test with real Tiingo (known ticker, short date range)
- [ ] Typecheck passes

---

### US-005: SQLite Cache Layer
**Description:** As a user, I want fetched data cached locally so repeated requests are instant and don't hit API rate limits.

**Acceptance Criteria:**
- [ ] Create `market_data/cache/database.py` with `PriceCache` class
- [ ] Create SQLite database at `~/.config/market-data/prices.db` on first use
- [ ] Implement schema: `prices` table with ticker, date, frequency, provider, OHLCV columns, adj_* columns, fetched_at
- [ ] Primary key: `(ticker, date, frequency, provider)`
- [ ] Implement `get_cached_data(ticker, start, end, frequency, provider)` → DataFrame
- [ ] Implement `get_missing_ranges(ticker, start, end, frequency, provider)` → List[DateRange]
- [ ] Implement `save_prices(ticker, frequency, provider, df)` with atomic transaction
- [ ] Implement `clear(ticker=None, provider=None)` for cache invalidation
- [ ] Raise `CacheError` with recovery instructions if database corrupted
- [ ] Unit tests for all methods
- [ ] Test atomic writes (partial data doesn't corrupt cache)
- [ ] Typecheck passes

---

### US-006: Rate Limiter
**Description:** As a user, I want rate limiting handled automatically so I don't get blocked by providers.

**Acceptance Criteria:**
- [ ] Create `RateLimiter` class in `market_data/api.py`
- [ ] Barchart: 0s delay between adj/unadj for same ticker
- [ ] Barchart: 2s delay between different tickers
- [ ] Barchart: 30s pause after every 10 tickers
- [ ] Tiingo: Track request counts (warn when approaching free tier limits)
- [ ] Rate limiter state persists across calls in same session
- [ ] Unit tests verify correct delays
- [ ] Typecheck passes

---

### US-007: Main API Function
**Description:** As a user, I want a simple `get_prices()` function that handles caching, provider selection, and rate limiting automatically.

**Acceptance Criteria:**
- [ ] Create `market_data/api.py` with `get_prices()` function
- [ ] Signature: `get_prices(ticker, start_date, end_date, frequency=DAILY, provider=AUTO, refresh=False) -> PriceData`
- [ ] `PriceData` dataclass contains: `df`, `ticker`, `provider`, `from_cache`, `from_api`, `start_date`, `end_date`
- [ ] Cache-first: query SQLite before calling provider
- [ ] Gap-filling: fetch only missing date ranges from provider
- [ ] `refresh=True` bypasses cache and fetches fresh data
- [ ] `provider=AUTO`: try Barchart first (if cookies valid), fall back to Tiingo
- [ ] `provider=BARCHART` or `provider=TIINGO`: use explicitly specified provider
- [ ] Validate ticker (1-10 chars, alphanumeric + "." + "-")
- [ ] Validate dates (start < end, not in future)
- [ ] Raise `ValueError` for invalid ticker/dates with clear message
- [ ] Only `frequency=DAILY` supported initially; others raise `ValueError`
- [ ] Return empty DataFrame (not error) if ticker exists but no data in range
- [ ] Unit tests with mocked cache and providers
- [ ] Integration test: fetch → verify cached → fetch again → verify from_cache > 0
- [ ] Typecheck passes

---

### US-008: Barchart Cookie Capture Script
**Description:** As a user, I need to capture fresh Barchart cookies so the provider works.

**Acceptance Criteria:**
- [ ] Create `market_data/refresh/capture_cookies.py` adapted from `ffn/capture_cookies_cdp.py`
- [ ] Rename `update_env_file()` to `save_cookies_json()`
- [ ] Write cookies to `~/.config/market-data/barchart_cookies.json`
- [ ] Include `captured_at` timestamp in ISO 8601 format
- [ ] Load username from `credentials.json`, password from env var specified in `barchart_password_env`
- [ ] Runnable as `python -m market_data.refresh.capture_cookies` (after `pyvenv`)
- [ ] Exit with clear error if credentials missing
- [ ] Exit with clear error if playwright not installed
- [ ] Manual test: run script, verify cookies file created
- [ ] Typecheck passes

---

### US-009: Cookie Refresh Automation (launchd)
**Description:** As a user, I want cookies refreshed automatically every 4 hours so Barchart access never expires.

**Acceptance Criteria:**
- [ ] Create `scripts/refresh-barchart-cookies` shell wrapper
- [ ] Shell script determines project root dynamically (relative to script location)
- [ ] Shell script sources the pyvenv activation and runs capture module
- [ ] Shell script logs output to `~/.config/market-data/logs/refresh-YYYY-MM-DD.log`
- [ ] Shell script is executable (`chmod +x`)
- [ ] Create `launchd/com.market-data.barchart-refresh.plist`
- [ ] Plist uses absolute path to `scripts/refresh-barchart-cookies`
- [ ] Plist sets working directory to project root
- [ ] Plist runs every 4 hours (14400 seconds)
- [ ] Plist runs on load (immediate first refresh)
- [ ] Document installation: copy plist to `~/Library/LaunchAgents/` then `launchctl load`
- [ ] User does NOT need to activate venv manually - script handles it via pyvenv
- [ ] Manual test: load plist, verify it runs, check logs
- [ ] Verify cookies stay fresh for 7+ days without manual intervention

---

### US-010: Exception Hierarchy
**Description:** As a developer, I need clear exception types so I can handle errors appropriately.

**Acceptance Criteria:**
- [ ] `MarketDataError` - base class for all library exceptions
- [ ] `ConfigurationError` - missing/invalid credentials (includes `credential_name`, `expected_location`)
- [ ] `ProviderError` - HTTP failures (includes `provider`, `status_code`, `response_body`)
- [ ] `CacheError` - SQLite failures (includes `operation`, recovery instructions)
- [ ] All exceptions inherit from `MarketDataError`
- [ ] All exceptions have clear, actionable `message`
- [ ] Unit tests verify exception attributes
- [ ] Typecheck passes

---

### US-011: Comprehensive Test Suite
**Description:** As a developer, I need a complete test suite so I can refactor with confidence.

**Acceptance Criteria:**
- [ ] `tests/unit/test_credentials.py` - mock filesystem, test all load paths and errors
- [ ] `tests/unit/test_cache.py` - test all PriceCache methods, including gap detection
- [ ] `tests/unit/test_providers.py` - mock HTTP, test success/retry/failure paths
- [ ] `tests/unit/test_api.py` - mock cache and providers, test all get_prices paths
- [ ] `tests/unit/test_rate_limiter.py` - test delay calculations
- [ ] `tests/integration/test_barchart.py` - real Barchart fetch (skipped if no cookies)
- [ ] `tests/integration/test_tiingo.py` - real Tiingo fetch (skipped if no API key)
- [ ] `tests/integration/test_end_to_end.py` - full flow: fetch → cache → refetch
- [ ] All tests run after `pyvenv` activation: `pytest tests/`
- [ ] Coverage report: `pytest --cov=market_data`
- [ ] Target: 90%+ coverage on business logic

---

### US-012: Documentation and Quickstart
**Description:** As a new user, I need clear documentation so I can get started quickly.

**Acceptance Criteria:**
- [ ] Create `README.md` with: overview, installation, quick start, API reference
- [ ] Document venv setup: `pyvenv` to create/activate, then `uv pip install -e ".[dev]"`
- [ ] Document that `pyvenv` handles venv activation transparently
- [ ] Document credential setup (`~/.config/market-data/credentials.json` format)
- [ ] Document cookie refresh setup (manual and automated via launchd)
- [ ] Document that launchd script handles venv activation automatically
- [ ] Include code examples for common use cases
- [ ] Document all exceptions and when they're raised
- [ ] Document rate limiting behavior
- [ ] Document how to run tests: `pytest tests/` (after `pyvenv`)

## Functional Requirements

- **FR-001**: The library MUST expose `get_prices(ticker, start_date, end_date)` as the primary public function
- **FR-002**: The library MUST return a `PriceData` object containing a pandas DataFrame
- **FR-003**: The DataFrame MUST include columns: Open, High, Low, Close, Volume, Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume
- **FR-004**: The library MUST check SQLite cache before calling provider APIs
- **FR-005**: The library MUST fetch only missing date ranges (gap-filling)
- **FR-006**: The library MUST support `refresh=True` to bypass cache
- **FR-007**: The library MUST support `provider=AUTO|BARCHART|TIINGO` parameter
- **FR-008**: `provider=AUTO` MUST try Barchart first, fall back to Tiingo
- **FR-009**: The library MUST validate ticker format (1-10 chars, alphanumeric + "." + "-")
- **FR-010**: The library MUST validate date range (start < end, not future)
- **FR-011**: The library MUST raise `ConfigurationError` for missing credentials
- **FR-012**: The library MUST raise `ProviderError` for HTTP failures (after retries)
- **FR-013**: The library MUST raise `CacheError` for SQLite failures
- **FR-014**: The library MUST enforce Barchart rate limits internally (2s between tickers, 30s every 10)
- **FR-015**: The library MUST store credentials in `~/.config/market-data/` (not in repo)
- **FR-016**: The library MUST have zero imports from the `ffn` package
- **FR-017**: The library MUST be installable via `uv pip install -e ".[dev]"` (after `pyvenv` activation)
- **FR-018**: Cookie refresh automation MUST run every 4 hours via launchd
- **FR-019**: All scripts (cookie refresh) MUST handle venv activation via pyvenv transparently
- **FR-020**: The `pyvenv` alias MUST be used for all venv management (no manual activation required)

## Non-Goals (Out of Scope)

- No CLI interface (library only, programmatic access)
- No web UI or dashboard
- No intraday data (daily frequency only)
- No support for futures, options, or forex (US equities only)
- No Windows/Linux automation (macOS launchd only; manual refresh on other platforms)
- No automatic priority/smart routing between providers (simple fallback only)
- No data quality validation beyond basic type checks
- No notification system for cookie expiry or API failures
- No use of system Python - all execution through pyvenv-managed environment
- No manual venv activation required - pyvenv handles it transparently

## Technical Considerations

- **Code Reuse**: Copy functions from `ffn` package per PLAN-v3 mappings; don't rewrite working code
- **Virtual Environment**: Use `pyvenv` alias to create and activate project venv transparently
- **Package Installation**: Use `uv` for fast, reliable package installation (`uv pip install`)
- **Dependencies**: pandas, requests, playwright, playwright-stealth (SQLite is built-in)
- **Dev Dependencies**: pytest, pytest-mock, pytest-cov, mypy, ruff (in pyproject.toml `[project.optional-dependencies]`)
- **Python Version**: 3.11+
- **Storage**: SQLite at `~/.config/market-data/prices.db`
- **Testing**: `pytest` (after `pyvenv` activation)
- **Linting**: `ruff check .`
- **Type Checking**: `mypy market_data/`

## Success Metrics

- Cache hit rate > 80% for repeated queries (measured via `from_cache` / total rows)
- Cached queries return in < 100ms
- Library handles 100 sequential ticker requests without rate limit errors
- Barchart cookies stay valid for 7+ days with automated refresh
- All tests pass with 90%+ coverage on business logic
- Zero `ffn` imports in final package

## Open Questions

- Should we add a `--verbose` mode to the cookie capture script for debugging?
- Should we log rate limiter delays for observability?
- What should happen if both providers fail for `provider=AUTO`? (Current plan: raise last ProviderError)
