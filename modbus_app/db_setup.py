"""
SQLite database optimization setup.
Apply performance optimizations and WAL mode.
"""

import logging

from django.db import connection

logger = logging.getLogger(__name__)


def setup_sqlite_optimizations():
    """
    Apply SQLite performance optimizations.
    Should be called once when Django starts.
    """
    try:
        with connection.cursor() as cursor:
            # Enable Write-Ahead Logging for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            result = cursor.fetchone()
            logger.info(f"SQLite journal_mode set to: {result[0]}")

            # Set synchronous mode to NORMAL (faster than FULL, still safe with WAL)
            cursor.execute("PRAGMA synchronous=NORMAL;")
            logger.info("SQLite synchronous mode set to NORMAL")

            # Increase cache size (10000 pages = ~40MB with default 4KB page size)
            cursor.execute("PRAGMA cache_size=10000;")
            logger.info("SQLite cache_size set to 10000 pages")

            # Use memory for temporary storage
            cursor.execute("PRAGMA temp_store=MEMORY;")
            logger.info("SQLite temp_store set to MEMORY")

            # Set busy timeout to 20 seconds
            cursor.execute("PRAGMA busy_timeout=20000;")
            logger.info("SQLite busy_timeout set to 20000ms")

            logger.info("SQLite optimizations applied successfully")

    except Exception as e:
        logger.error(f"Failed to apply SQLite optimizations: {e}")
        # Don't raise - let app continue even if optimization fails


def get_sqlite_info():
    """Get current SQLite configuration for debugging."""
    info = {}
    try:
        with connection.cursor() as cursor:
            # Get journal mode
            cursor.execute("PRAGMA journal_mode;")
            info["journal_mode"] = cursor.fetchone()[0]

            # Get synchronous mode
            cursor.execute("PRAGMA synchronous;")
            info["synchronous"] = cursor.fetchone()[0]

            # Get cache size
            cursor.execute("PRAGMA cache_size;")
            info["cache_size"] = cursor.fetchone()[0]

            # Get temp store
            cursor.execute("PRAGMA temp_store;")
            info["temp_store"] = cursor.fetchone()[0]

    except Exception as e:
        logger.error(f"Failed to get SQLite info: {e}")

    return info
