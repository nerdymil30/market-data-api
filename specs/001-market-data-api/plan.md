# Implementation Plan: Market Data API Library

**Branch**: `001-market-data-api` | **Date**: 2026-01-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-market-data-api/spec.md`

## Summary

Create a self-contained Python library for fetching historical market data with cache-first architecture. The library exposes a simple `get_prices()` API that fetches OHLCV data from Barchart or Tiingo providers, caches results in SQLite, and returns both adjusted and unadjusted prices. Implementation follows a code-reuse strategy: copy and refactor existing debugged code from the `ffn` package per the mappings in `PLAN-v3-reuse-existing-code.md`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pandas, requests, playwright, playwright-stealth
**Storage**: SQLite (built-in) at `~/.config/market-data/prices.db`
**Testing**: pytest, pytest-mock
**Target Platform**: macOS (launchd for cookie refresh); library works on any Python platform
**Project Type**: Single Python package (library)
**Performance Goals**: <100ms for cached queries; handle 100 sequential ticker requests without rate limit errors
**Constraints**: Barchart rate limits (2s between tickers, 30s pause every 10); Tiingo API tier limits
**Scale/Scope**: Single-user local library; US equities daily data only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. API-First Design | ✅ PASS | `get_prices()` is the single public entry point; internal modules not exposed |
| II. Data Integrity & Accuracy | ✅ PASS | Both adj/unadj prices returned; provider tracked in metadata; NaN for missing |
| III. Cache-First Architecture | ✅ PASS | SQLite cache checked first; gap-filling for missing ranges; `refresh=True` bypass |
| IV. Credential Security | ✅ PASS | Credentials in `~/.config/market-data/`; never logged; explicit errors on missing |
| V. Provider Abstraction | ✅ PASS | Barchart and Tiingo implement same contract; rate limits encapsulated; AUTO mode |
| VI. Test-First Development | ✅ PASS | pytest with mocked providers for unit tests; integration tests planned |
| VII. Fail-Fast & Explicit Errors | ✅ PASS | Custom exception hierarchy: `MarketDataError` → `ConfigurationError`, `ProviderError`, `CacheError` |

**Gate Result**: PASS - All constitution principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-market-data-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (Python API contract)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
market_data/
├── __init__.py           # Public API exports: get_prices, Frequency, Provider, PriceData
├── api.py                # Main get_prices() implementation with cache-first logic
├── credentials.py        # Credential loading from ~/.config/market-data/
├── exceptions.py         # Custom exception hierarchy
├── cache/
│   ├── __init__.py
│   └── database.py       # SQLite cache: PriceCache class
├── providers/
│   ├── __init__.py
│   ├── base.py           # Provider interface/contract (optional)
│   ├── barchart.py       # Barchart provider (adapted from ffn/barchart_provider.py)
│   └── tiingo.py         # Tiingo provider (adapted from ffn/tiingo_provider.py)
└── refresh/
    ├── __init__.py
    └── capture_cookies.py  # Barchart cookie capture (adapted from ffn/capture_cookies_cdp.py)

scripts/
└── refresh-barchart-cookies  # Shell wrapper for cookie refresh

launchd/
└── com.market-data.barchart-refresh.plist  # 4-hour refresh schedule

tests/
├── unit/
│   ├── test_api.py
│   ├── test_cache.py
│   ├── test_credentials.py
│   └── test_providers.py
└── integration/
    └── test_end_to_end.py

pyproject.toml            # Package configuration
```

**Structure Decision**: Single Python package structure. The library is standalone with no web/mobile components. Source files are adapted from existing `ffn` package per PLAN-v3 mappings.

## Source Code Mapping (from PLAN-v3)

| Target File | Source | Adaptation Required |
|-------------|--------|---------------------|
| `market_data/providers/barchart.py` | `ffn/barchart_provider.py` | Remove `ffn` imports; load cookies from JSON |
| `market_data/providers/tiingo.py` | `ffn/tiingo_provider.py` | Remove `ffn` imports; load API key from JSON |
| `market_data/credentials.py` | `ffn/barchart_cookies.py` | Read from `~/.config/market-data/*.json` |
| `market_data/refresh/capture_cookies.py` | `ffn/capture_cookies_cdp.py` | Output to JSON instead of `.env` |
| `market_data/cache/database.py` | **New code** | SQLite caching layer |
| `market_data/api.py` | Pattern from `etf_price_capture.py` | Cache-first logic; `get_prices()` API |
| `market_data/exceptions.py` | **New code** | Custom exception hierarchy |

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
