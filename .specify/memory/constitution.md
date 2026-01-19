<!--
SYNC IMPACT REPORT
==================
Version change: 0.0.0 → 1.0.0 (MAJOR - initial constitution creation)

Modified principles: N/A (initial version)

Added sections:
- Core Principles (7 principles)
  - I. API-First Design
  - II. Data Integrity & Accuracy
  - III. Cache-First Architecture
  - IV. Credential Security
  - V. Provider Abstraction
  - VI. Test-First Development
  - VII. Fail-Fast & Explicit Errors
- Financial Data Constraints
- Development Workflow
- Governance

Removed sections: None (initial version)

Templates requiring updates:
- .specify/templates/plan-template.md ✅ (compatible - Constitution Check section exists)
- .specify/templates/spec-template.md ✅ (compatible - Requirements section aligns)
- .specify/templates/tasks-template.md ✅ (compatible - Phase structure supports principles)

Follow-up TODOs: None
-->

# Market Data API Constitution

## Core Principles

### I. API-First Design

The library MUST expose a simple, intuitive public API as the primary interface.

- All functionality MUST be accessible through the documented public API (`get_prices()`, `Frequency`, `Provider`)
- Internal modules (`providers/`, `cache/`, `refresh/`) MUST NOT be imported directly by consumers
- Public API signatures MUST remain stable within a major version; breaking changes require a major version bump
- Return types MUST be predictable: `PriceData` objects containing pandas DataFrames with standardized column names

**Rationale**: Financial applications require stable, well-documented interfaces. API stability enables
consumers to build reliable trading systems and analytics without fear of breaking changes.

### II. Data Integrity & Accuracy

Financial data MUST be accurate, complete, and traceable to its source.

- All price data MUST include both adjusted and unadjusted values (Open, High, Low, Close, Volume)
- Data provenance MUST be tracked: every DataFrame MUST identify its source provider
- Missing data MUST be explicitly represented (NaN), never silently filled or interpolated
- Date ranges MUST be validated: start_date < end_date, dates MUST be valid trading days or weekends/holidays handled explicitly
- Ticker symbols MUST be validated before API calls to providers

**Rationale**: Inaccurate financial data leads to incorrect investment decisions. Explicit handling of
missing data and clear provenance enables consumers to make informed decisions about data quality.

### III. Cache-First Architecture

The library MUST minimize external API calls through intelligent caching.

- SQLite cache MUST be the first lookup source for all data requests
- Only missing date ranges MUST trigger provider API calls
- Cache writes MUST be atomic: partial data MUST NOT corrupt existing cache entries
- Cache schema MUST include `fetched_at` timestamps for staleness detection
- The `refresh=True` parameter MUST bypass cache for explicit refresh requests
- Cache location: `~/.config/market-data/prices.db`

**Rationale**: External data providers have rate limits and costs. Cache-first design reduces API calls,
improves response times, and enables offline development/testing scenarios.

### IV. Credential Security

Credentials MUST be stored securely and never logged or exposed.

- All credentials MUST be stored in `~/.config/market-data/` with appropriate file permissions
- API keys and passwords MUST NEVER appear in logs, error messages, or stack traces
- Credential loading MUST fail explicitly if required credentials are missing
- Barchart cookies MUST be auto-refreshed via launchd (every 4 hours) to maintain valid sessions
- Credentials JSON structure MUST be documented and validated on load

**Rationale**: Financial API credentials provide access to paid services and potentially sensitive data.
Credential leakage can result in unauthorized access and financial liability.

### V. Provider Abstraction

Multiple data providers MUST be supported through a consistent internal interface.

- Each provider MUST implement the same internal contract: `fetch_prices(ticker, start, end, frequency) -> DataFrame`
- Provider-specific quirks MUST be encapsulated within provider modules
- Rate limiting MUST be provider-specific and enforced internally:
  - Barchart: 0s between adj/unadj for same ticker, 2s between tickers, 30s pause every 10 tickers
  - Tiingo: Per their API documentation
- Provider selection MUST support AUTO mode (intelligent fallback) and explicit provider selection

**Rationale**: No single data provider is perfect. Provider abstraction enables fallback strategies,
comparison of data sources, and resilience against provider outages.

### VI. Test-First Development

All new functionality MUST be developed using Test-Driven Development (TDD).

- Tests MUST be written before implementation (Red-Green-Refactor cycle)
- Unit tests MUST mock external provider APIs to ensure deterministic results
- Integration tests MUST use real providers but with known test tickers and date ranges
- Cache tests MUST verify atomic writes, missing range detection, and staleness handling
- All tests MUST pass before code is merged to main branch

**Rationale**: Financial libraries require high reliability. TDD ensures comprehensive test coverage
and prevents regressions that could lead to incorrect data or silent failures.

### VII. Fail-Fast & Explicit Errors

Errors MUST be raised early with clear, actionable messages.

- Invalid tickers MUST raise `ValueError` with the invalid ticker and validation rules
- Missing credentials MUST raise `ConfigurationError` with the missing credential name and expected location
- Provider errors MUST raise `ProviderError` with the provider name, HTTP status, and response body
- Cache corruption MUST raise `CacheError` with recovery instructions
- All custom exceptions MUST inherit from a base `MarketDataError` class

**Rationale**: Silent failures in financial systems lead to incorrect calculations and decisions.
Explicit errors enable rapid debugging and prevent cascading failures.

## Financial Data Constraints

### Data Quality Standards

- Price precision: MUST maintain at least 4 decimal places for prices
- Volume: MUST be stored as integers (no fractional shares in historical data)
- Timestamps: All dates MUST be stored in ISO 8601 format (YYYY-MM-DD)
- Timezone: All timestamps MUST be in market timezone (US/Eastern for US equities) unless explicitly converted

### Provider-Specific Handling

- Barchart: Requires browser cookies; auto-refresh MUST be configured via launchd
- Tiingo: Requires API key; free tier limits MUST be documented
- Both providers: HTTP retry logic MUST handle transient failures (429, 500, 503)

### Rate Limiting Compliance

The library MUST respect provider rate limits to avoid account suspension:

| Provider | Constraint | Limit |
|----------|------------|-------|
| Barchart | Between adj/unadj same ticker | 0 seconds |
| Barchart | Between different tickers | 2 seconds |
| Barchart | After every 10 tickers | 30 seconds pause |
| Tiingo | Per API documentation | Varies by tier |

## Development Workflow

### Code Organization

```
market_data/
├── __init__.py       # Public API exports only
├── api.py            # get_prices() implementation
├── credentials.py    # Credential loading and validation
├── exceptions.py     # Custom exception hierarchy
├── cache/
│   └── database.py   # SQLite cache implementation
├── providers/
│   ├── base.py       # Provider interface/contract
│   ├── barchart.py   # Barchart implementation
│   └── tiingo.py     # Tiingo implementation
└── refresh/
    └── capture_cookies.py  # Barchart cookie refresh
```

### Dependency Management

- Runtime dependencies MUST be minimal: `pandas`, `requests`, `playwright`, `playwright-stealth`
- SQLite is built into Python and MUST NOT require additional dependencies
- Development dependencies MUST be separate: `pytest`, `pytest-mock`, `mypy`, `ruff`

### Code Quality Gates

All code MUST pass these checks before merge:

1. `ruff check .` - No linting errors
2. `ruff format --check .` - Consistent formatting
3. `mypy market_data/` - Type checking passes
4. `pytest tests/` - All tests pass
5. No credentials or secrets in committed code

## Governance

### Amendment Process

1. Propose amendment via PR with rationale
2. Update constitution version following semantic versioning:
   - MAJOR: Principle removal or backward-incompatible changes
   - MINOR: New principles or material expansions
   - PATCH: Clarifications and typo fixes
3. Update `LAST_AMENDED_DATE` to current date
4. Ensure all dependent templates remain consistent

### Compliance Verification

- All PRs MUST include a constitution compliance checklist
- Code reviews MUST verify adherence to relevant principles
- Exceptions to principles MUST be documented with justification in the Complexity Tracking section of the implementation plan

### Runtime Guidance

For day-to-day development decisions not covered by this constitution, refer to:
- `PLAN-v3-reuse-existing-code.md` for architecture decisions
- Provider documentation for API-specific constraints
- Python best practices (PEP 8, PEP 484 type hints)

**Version**: 1.0.0 | **Ratified**: 2026-01-19 | **Last Amended**: 2026-01-19
