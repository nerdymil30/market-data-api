# Feature Specification: Market Data API Library

**Feature Branch**: `001-market-data-api`
**Created**: 2026-01-19
**Status**: Draft
**Input**: User description: "Create a self-contained market data API library with cache-first architecture"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fetch Historical Price Data (Priority: P1)

As a quantitative analyst or developer, I want to retrieve historical price data for a stock ticker by specifying the ticker symbol and date range, so that I can perform financial analysis without worrying about data provider details or rate limits.

**Why this priority**: This is the core functionality of the library. Without the ability to fetch price data, no other features have value. This enables the primary use case of getting market data for analysis.

**Independent Test**: Can be fully tested by calling `get_prices("SPY", "2024-01-01", "2024-01-31")` and verifying it returns a structured result with price data (Open, High, Low, Close, Volume) for the requested date range.

**Acceptance Scenarios**:

1. **Given** valid credentials are configured and the library is installed, **When** I call `get_prices("AAPL", "2024-01-01", "2024-12-31")`, **Then** I receive a result containing a DataFrame with daily OHLCV data for the requested period.

2. **Given** valid credentials are configured, **When** I request data for an invalid ticker like "XXXXXX", **Then** I receive a clear error message indicating the ticker is invalid.

3. **Given** valid credentials are configured, **When** I request data with an invalid date range (end_date before start_date), **Then** I receive a clear error message about the invalid date range.

---

### User Story 2 - Cache-First Data Retrieval (Priority: P2)

As a developer building a financial application, I want the library to automatically cache fetched data locally, so that repeated requests for the same data are fast and don't consume API rate limits.

**Why this priority**: Caching dramatically improves performance for repeated queries and prevents hitting provider rate limits. This is essential for any production use but requires the core fetch functionality (P1) to work first.

**Independent Test**: Can be tested by fetching data twice for the same ticker/date range and verifying the second request returns instantly with `from_cache > 0` in the result metadata.

**Acceptance Scenarios**:

1. **Given** I have previously fetched data for "SPY" from 2024-01-01 to 2024-01-31, **When** I request the same data again, **Then** the result indicates data came from cache (from_cache count > 0) and the response is near-instantaneous.

2. **Given** I have cached data for "SPY" from 2024-01-01 to 2024-01-15, **When** I request data for 2024-01-01 to 2024-01-31, **Then** only the missing dates (2024-01-16 to 2024-01-31) are fetched from the provider and the result combines cached and fresh data.

3. **Given** I have cached data for a ticker, **When** I call `get_prices()` with `refresh=True`, **Then** the cache is bypassed and fresh data is fetched from the provider.

---

### User Story 3 - Multiple Data Providers (Priority: P3)

As a quantitative analyst, I want to choose between different data providers (Barchart, Tiingo) or let the library auto-select, so that I can use the provider that best fits my needs or have fallback options.

**Why this priority**: Provider flexibility adds resilience and choice but isn't required for basic functionality. Users can start with a single default provider.

**Independent Test**: Can be tested by explicitly specifying `provider=Provider.TIINGO` and verifying data is fetched from Tiingo, then specifying `provider=Provider.BARCHART` and verifying data is fetched from Barchart.

**Acceptance Scenarios**:

1. **Given** I have configured Tiingo credentials, **When** I call `get_prices("AAPL", "2024-01-01", "2024-01-31", provider=Provider.TIINGO)`, **Then** data is fetched from Tiingo and the result metadata shows provider="tiingo".

2. **Given** I have configured Barchart credentials (cookies), **When** I call `get_prices("AAPL", "2024-01-01", "2024-01-31", provider=Provider.BARCHART)`, **Then** data is fetched from Barchart and the result metadata shows provider="barchart".

3. **Given** I specify `provider=Provider.AUTO` and both providers are configured, **When** I request data, **Then** the library attempts Barchart first (if cookies are valid), falling back to Tiingo if Barchart fails.

---

### User Story 4 - Adjusted and Unadjusted Prices (Priority: P4)

As a financial analyst, I want to receive both adjusted and unadjusted price data in each response, so that I can use the appropriate values for different types of analysis (adjusted for returns, unadjusted for order execution).

**Why this priority**: Having both price types is important for comprehensive analysis but the library can deliver value with just one price type initially.

**Independent Test**: Can be tested by fetching data and verifying the DataFrame contains both sets of columns: Open/High/Low/Close/Volume AND Adj_Open/Adj_High/Adj_Low/Adj_Close/Adj_Volume.

**Acceptance Scenarios**:

1. **Given** valid credentials are configured, **When** I fetch price data for any ticker, **Then** the resulting DataFrame contains columns for both unadjusted prices (Open, High, Low, Close, Volume) and adjusted prices (Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume).

2. **Given** the ticker has had a stock split, **When** I fetch historical data spanning before and after the split, **Then** the adjusted prices reflect the split adjustment while unadjusted prices show original values.

---

### User Story 5 - Automated Credential Refresh (Priority: P5)

As a system administrator, I want Barchart authentication cookies to be automatically refreshed on a schedule, so that the library continues to work without manual intervention.

**Why this priority**: Automation is a convenience feature that prevents credential expiration issues but requires manual setup initially. Users can manually refresh cookies if needed.

**Independent Test**: Can be tested by running the cookie refresh script and verifying new cookies are saved to the expected location with a fresh timestamp.

**Acceptance Scenarios**:

1. **Given** valid Barchart credentials are configured, **When** I run the cookie refresh script, **Then** fresh cookies are captured and saved to `~/.config/market-data/barchart_cookies.json` with an updated timestamp.

2. **Given** the launchd schedule is configured, **When** 4 hours have passed since the last refresh, **Then** cookies are automatically refreshed without user intervention.

---

### Edge Cases

- What happens when credentials are missing or expired?
  - The library MUST raise a clear `ConfigurationError` with the missing credential name and expected file path.

- What happens when the data provider is temporarily unavailable (HTTP 500, 503)?
  - The library MUST retry with exponential backoff (up to 3 attempts) before raising a `ProviderError`.

- What happens when rate limits are exceeded?
  - The library MUST wait according to provider-specific rate limit rules and retry automatically.

- What happens when requesting data for a weekend or market holiday?
  - The library MUST return data for the nearest valid trading days within the requested range (no error, just fewer rows).

- What happens when the cache database file is corrupted?
  - The library MUST raise a `CacheError` with instructions for recovery (delete and recreate).

- What happens when the ticker exists but has no data for the requested date range?
  - The library MUST return an empty DataFrame (not an error) with the correct column structure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Library MUST expose a simple public function `get_prices(ticker, start_date, end_date, frequency=Frequency.DAILY)` as the primary interface. Only DAILY frequency is supported initially; other values MUST raise `ValueError`.
- **FR-002**: Library MUST return a `PriceData` object containing a pandas DataFrame with standardized column names.
- **FR-003**: Library MUST store credentials in `~/.config/market-data/` directory in JSON format.
- **FR-004**: Library MUST cache all fetched price data in a local SQLite database.
- **FR-005**: Library MUST fetch only missing date ranges when cached data exists (intelligent gap-filling).
- **FR-006**: Library MUST support both Barchart and Tiingo as data providers.
- **FR-007**: Library MUST enforce provider-specific rate limits automatically (no user configuration required).
- **FR-008**: Library MUST return both adjusted and unadjusted OHLCV data in each response.
- **FR-009**: Library MUST validate ticker symbols before making provider API calls.
- **FR-010**: Library MUST validate date ranges (start_date < end_date, valid date formats).
- **FR-011**: Library MUST support a `refresh=True` parameter to bypass cache and fetch fresh data.
- **FR-012**: Library MUST support a `provider` parameter to explicitly select data provider.
- **FR-013**: Library MUST provide a script to refresh Barchart cookies.
- **FR-014**: Library MUST include metadata in results: ticker, provider, from_cache count, from_api count.
- **FR-015**: Library MUST be installable as a standalone package with `pip install`.
- **FR-016**: Library MUST have no dependencies on the original `ffn` package.
- **FR-017**: Library MUST raise specific exception types: `ConfigurationError`, `ProviderError`, `CacheError`, all inheriting from `MarketDataError`.

### Key Entities

- **PriceData**: The result object returned by `get_prices()`. Contains the price DataFrame plus metadata (ticker, provider, cache statistics).
- **Price Record**: A single row of price data for one ticker on one date. Attributes: ticker, date, frequency, provider, open, high, low, close, volume, adj_open, adj_high, adj_low, adj_close, adj_volume, fetched_at.
- **Credentials**: Configuration data needed to authenticate with data providers. Tiingo requires an API key; Barchart requires browser cookies.
- **Provider**: An abstraction representing a data source (Barchart or Tiingo). Each provider has its own authentication method and rate limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can retrieve price data for any US equity ticker with a single function call.
- **SC-002**: Cached data requests return results in under 100 milliseconds.
- **SC-003**: The library correctly identifies and fetches only missing date ranges, reducing API calls by at least 80% for overlapping requests.
- **SC-004**: The library handles 100 sequential ticker requests without rate limit errors.
- **SC-005**: All price data includes both adjusted and unadjusted values (10 columns total).
- **SC-006**: Error messages include actionable information (what failed, expected format/location, how to fix).
- **SC-007**: The library can be installed and used with zero configuration files if credentials are pre-populated in `~/.config/market-data/`.
- **SC-008**: Cookie refresh automation keeps Barchart access working continuously for at least 7 days without manual intervention.

## Assumptions

- Users have valid credentials for at least one data provider (Barchart or Tiingo).
- Users are fetching US equity data (stocks, ETFs). Other asset classes (futures, options, forex) are out of scope.
- The host system is macOS (for launchd-based cookie refresh automation). Linux cron support is out of scope for initial release.
- Data frequency is daily. Intraday data support is out of scope for initial release.
- The `~/.config/market-data/` directory is writable by the user running the library.

## Implementation Strategy

- **Source Code Reuse**: Implementation MUST copy and refactor existing debugged code from the `ffn` package rather than writing from scratch.
- **Authoritative Mapping**: `PLAN-v3-reuse-existing-code.md` is the authoritative document for source→target file mappings.
- **Mapping Updates**: The planning phase should verify source files exist and update mappings only if necessary (e.g., source file moved or renamed).

## Clarifications

### Session 2026-01-19

- Q: What is the source code reuse strategy? → A: PLAN-v3 is the authoritative source mapping document; comply with existing mappings and verify/update only as necessary.
- Q: Provider.AUTO selection priority when both configured? → A: Barchart first (if cookies valid), Tiingo as fallback.
- Q: Should frequency parameter exist even if only DAILY supported? → A: Yes, include `frequency=Frequency.DAILY` parameter for future extensibility.
