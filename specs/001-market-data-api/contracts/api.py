"""
Market Data API Contract

This file defines the public API contract for the market_data library.
It serves as documentation and a reference for implementation.

Usage:
    from market_data import get_prices, Frequency, Provider, PriceData

Note: This is a CONTRACT file, not the actual implementation.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional, Union

import pandas as pd


# =============================================================================
# Enums
# =============================================================================


class Frequency(Enum):
    """Data frequency options."""

    DAILY = "daily"
    # Future extensions:
    # WEEKLY = "weekly"
    # MONTHLY = "monthly"


class Provider(Enum):
    """Data provider options."""

    BARCHART = "barchart"
    TIINGO = "tiingo"
    AUTO = "auto"  # Barchart first, Tiingo fallback


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class PriceData:
    """
    Result object returned by get_prices().

    Attributes:
        df: DataFrame with OHLCV columns (both adjusted and unadjusted).
            Index is DatetimeIndex.
            Columns: Open, High, Low, Close, Volume,
                     Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume
        ticker: The requested ticker symbol (uppercase).
        provider: The data source used ("barchart" or "tiingo").
        from_cache: Number of rows retrieved from local cache.
        from_api: Number of rows fetched from provider API.
        start_date: Requested start date.
        end_date: Requested end date.
    """

    df: pd.DataFrame
    ticker: str
    provider: str
    from_cache: int
    from_api: int
    start_date: date
    end_date: date


# =============================================================================
# Exceptions
# =============================================================================


class MarketDataError(Exception):
    """Base exception for all market_data errors."""

    pass


class ConfigurationError(MarketDataError):
    """
    Raised when credentials are missing or invalid.

    Attributes:
        credential_name: The missing or invalid credential.
        expected_location: Where the credential should be.
        message: Human-readable error message with fix instructions.
    """

    def __init__(
        self, credential_name: str, expected_location: str, message: str
    ) -> None:
        self.credential_name = credential_name
        self.expected_location = expected_location
        super().__init__(message)


class ProviderError(MarketDataError):
    """
    Raised when a data provider request fails.

    Attributes:
        provider: The provider that failed ("barchart" or "tiingo").
        status_code: HTTP status code (if applicable).
        response_body: Response content for debugging.
        message: Human-readable error message.
    """

    def __init__(
        self,
        provider: str,
        status_code: Optional[int],
        response_body: Optional[str],
        message: str,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class CacheError(MarketDataError):
    """
    Raised when cache operations fail.

    Attributes:
        operation: The operation that failed (read/write).
        message: Human-readable error message with recovery instructions.
    """

    def __init__(self, operation: str, message: str) -> None:
        self.operation = operation
        super().__init__(message)


# =============================================================================
# Main API Function
# =============================================================================


def get_prices(
    ticker: str,
    start_date: Union[str, date],
    end_date: Union[str, date],
    frequency: Frequency = Frequency.DAILY,
    provider: Provider = Provider.AUTO,
    refresh: bool = False,
) -> PriceData:
    """
    Fetch historical price data for a ticker.

    This is the primary entry point for the market_data library.
    Uses cache-first strategy: checks local SQLite cache before
    calling provider APIs.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "SPY").
            Will be converted to uppercase.
            Must be 1-10 alphanumeric characters (plus "." and "-").

        start_date: Start of date range (inclusive).
            Accepts ISO format string "YYYY-MM-DD" or date object.

        end_date: End of date range (inclusive).
            Accepts ISO format string "YYYY-MM-DD" or date object.
            Must be after start_date.

        frequency: Data frequency. Default: Frequency.DAILY.
            Currently only DAILY is supported.
            Other values raise ValueError.

        provider: Data provider selection. Default: Provider.AUTO.
            - BARCHART: Use Barchart (requires valid cookies)
            - TIINGO: Use Tiingo (requires API key)
            - AUTO: Try Barchart first, fall back to Tiingo

        refresh: If True, bypass cache and fetch fresh data.
            Default: False.

    Returns:
        PriceData object containing:
            - df: DataFrame with OHLCV data (adjusted + unadjusted)
            - Metadata: ticker, provider, cache/api row counts

    Raises:
        ValueError: If ticker, dates, or frequency are invalid.
        ConfigurationError: If required credentials are missing.
        ProviderError: If provider request fails after retries.
        CacheError: If cache read/write fails.

    Examples:
        # Simple usage
        >>> data = get_prices("AAPL", "2024-01-01", "2024-12-31")
        >>> print(data.df.head())

        # Explicit provider
        >>> data = get_prices("SPY", "2024-01-01", "2024-01-31",
        ...                   provider=Provider.TIINGO)

        # Force refresh (bypass cache)
        >>> data = get_prices("MSFT", "2024-06-01", "2024-06-30",
        ...                   refresh=True)

    Notes:
        - Data includes both adjusted and unadjusted prices.
        - Weekends and market holidays return no rows (not errors).
        - Missing data is represented as NaN, not filled.
        - Rate limits are enforced internally per provider.
    """
    # CONTRACT: Implementation in market_data/api.py
    raise NotImplementedError("This is a contract file")


# =============================================================================
# Public API Exports
# =============================================================================

__all__ = [
    # Main function
    "get_prices",
    # Enums
    "Frequency",
    "Provider",
    # Result types
    "PriceData",
    # Exceptions
    "MarketDataError",
    "ConfigurationError",
    "ProviderError",
    "CacheError",
]
