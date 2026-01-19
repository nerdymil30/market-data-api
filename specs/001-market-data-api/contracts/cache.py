"""
Cache Contract

This file defines the internal contract for the SQLite cache layer.
The cache is internal to the library and not exposed to consumers.

Note: This is a CONTRACT file, not the actual implementation.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class DateRange:
    """Represents a contiguous date range."""

    start: date
    end: date


class PriceCache:
    """
    SQLite cache for price data.

    Implements cache-first lookup with intelligent gap detection.
    Stored at ~/.config/market-data/prices.db

    Thread Safety:
        Single-threaded access assumed. SQLite handles basic
        file locking but concurrent writes are not optimized.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize cache connection.

        Args:
            db_path: Path to SQLite database.
                Default: ~/.config/market-data/prices.db

        Creates database and schema if not exists.
        """
        # CONTRACT: Initialize SQLite connection
        raise NotImplementedError()

    def get_cached_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        frequency: str,
        provider: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Retrieve cached price data.

        Args:
            ticker: Stock ticker symbol.
            start_date: Start of date range.
            end_date: End of date range.
            frequency: Data frequency ("daily").
            provider: Optional provider filter.
                If None, returns data from any provider.

        Returns:
            DataFrame with cached data.
            Empty DataFrame if no cached data exists.
            Columns match PriceRecord schema.

        Raises:
            CacheError: If database read fails.
        """
        # CONTRACT: Query SQLite and return DataFrame
        raise NotImplementedError()

    def get_missing_ranges(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        frequency: str,
        provider: Optional[str] = None,
    ) -> List[DateRange]:
        """
        Identify date ranges not present in cache.

        This enables intelligent gap-filling: only fetch
        dates that aren't already cached.

        Args:
            ticker: Stock ticker symbol.
            start_date: Start of requested range.
            end_date: End of requested range.
            frequency: Data frequency.
            provider: Optional provider filter.

        Returns:
            List of DateRange objects representing gaps.
            Empty list if all dates are cached.

        Examples:
            # Cached: Jan 1-10, Jan 20-31
            # Requested: Jan 1-31
            # Returns: [DateRange(Jan 11, Jan 19)]
        """
        # CONTRACT: Analyze cache and identify gaps
        raise NotImplementedError()

    def save_prices(
        self,
        ticker: str,
        frequency: str,
        provider: str,
        df: pd.DataFrame,
    ) -> int:
        """
        Save price data to cache.

        Uses INSERT OR REPLACE for upsert behavior.
        Operation is atomic (transaction).

        Args:
            ticker: Stock ticker symbol.
            frequency: Data frequency.
            provider: Data source.
            df: DataFrame with price data.
                Index: date
                Columns: open, high, low, close, volume,
                         adj_open, adj_high, adj_low, adj_close, adj_volume

        Returns:
            Number of rows inserted/updated.

        Raises:
            CacheError: If database write fails.
        """
        # CONTRACT: Insert/update rows in SQLite
        raise NotImplementedError()

    def clear(
        self,
        ticker: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> int:
        """
        Clear cached data.

        Args:
            ticker: If provided, only clear this ticker.
            provider: If provided, only clear this provider.
            If both None, clears entire cache.

        Returns:
            Number of rows deleted.
        """
        # CONTRACT: Delete rows from cache
        raise NotImplementedError()

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with:
                - total_rows: int
                - unique_tickers: int
                - oldest_data: date
                - newest_data: date
                - db_size_mb: float
        """
        # CONTRACT: Query cache metadata
        raise NotImplementedError()

    def close(self) -> None:
        """Close database connection."""
        raise NotImplementedError()


# =============================================================================
# SQL Schema Reference
# =============================================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prices (
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

CREATE INDEX IF NOT EXISTS idx_ticker_date
ON prices (ticker, date);
"""
