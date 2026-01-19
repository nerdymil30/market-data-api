"""
Provider Contract

This file defines the internal contract that all data providers must implement.
Providers are internal to the library and not exposed to consumers.

Note: This is a CONTRACT file, not the actual implementation.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

import pandas as pd


class BaseProvider(ABC):
    """
    Abstract base class for data providers.

    All providers (Barchart, Tiingo) must implement this interface.
    This ensures consistent behavior across providers and enables
    the AUTO fallback mechanism.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider identifier.

        Returns:
            "barchart" or "tiingo"
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if provider credentials are available.

        Returns:
            True if credentials exist and appear valid.
            Does not verify credentials work (no API call).
        """
        pass

    @abstractmethod
    def fetch_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """
        Fetch price data from the provider.

        This method handles rate limiting internally.
        It fetches both adjusted and unadjusted prices.

        Args:
            ticker: Validated uppercase ticker symbol.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            frequency: Data frequency ("daily" only for now).

        Returns:
            DataFrame with columns:
                - date (index): Trading date
                - open, high, low, close, volume: Unadjusted
                - adj_open, adj_high, adj_low, adj_close, adj_volume: Adjusted

            Empty DataFrame (with correct columns) if no data available.

        Raises:
            ProviderError: If request fails after retries.
            ConfigurationError: If credentials are invalid.
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Verify credentials by making a lightweight API call.

        Returns:
            True if credentials are valid and working.
            False if credentials are expired or invalid.

        Raises:
            ConfigurationError: If credentials are missing.
        """
        pass


class BarchartProvider(BaseProvider):
    """
    Barchart data provider.

    Requires browser cookies for authentication.
    Cookies are stored in ~/.config/market-data/barchart_cookies.json

    Rate limits:
        - 0s between adj/unadj queries for same ticker
        - 2s between different tickers
        - 30s pause after every 10 tickers
    """

    @property
    def name(self) -> str:
        return "barchart"

    def is_configured(self) -> bool:
        # CONTRACT: Check if barchart_cookies.json exists
        raise NotImplementedError()

    def fetch_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        # CONTRACT: Implementation adapted from ffn/barchart_provider.py
        # Makes 2 requests: adjusted and unadjusted
        raise NotImplementedError()

    def validate_credentials(self) -> bool:
        # CONTRACT: Make lightweight request to verify cookies
        raise NotImplementedError()


class TiingoProvider(BaseProvider):
    """
    Tiingo data provider.

    Requires API key for authentication.
    API key stored in ~/.config/market-data/credentials.json

    Rate limits:
        - Free tier: 500 requests/day, 50 requests/hour
        - Paid tiers: Higher limits
    """

    @property
    def name(self) -> str:
        return "tiingo"

    def is_configured(self) -> bool:
        # CONTRACT: Check if tiingo_api_key exists in credentials.json
        raise NotImplementedError()

    def fetch_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        # CONTRACT: Implementation adapted from ffn/tiingo_provider.py
        raise NotImplementedError()

    def validate_credentials(self) -> bool:
        # CONTRACT: Make lightweight request to verify API key
        raise NotImplementedError()


# =============================================================================
# Provider Factory
# =============================================================================


def get_provider(provider_name: str) -> BaseProvider:
    """
    Get a provider instance by name.

    Args:
        provider_name: "barchart" or "tiingo"

    Returns:
        Provider instance.

    Raises:
        ValueError: If provider_name is unknown.
    """
    # CONTRACT: Return appropriate provider instance
    raise NotImplementedError()
