"""Retry utilities for AWS API throttling."""

from __future__ import annotations

import functools
import logging
import time

import botocore.exceptions

from cloud_mapper.config import INITIAL_BACKOFF, MAX_RETRIES

logger = logging.getLogger(__name__)


def retry_on_throttle(func):
    """Decorator that retries on AWS throttling errors with exponential backoff."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        backoff = INITIAL_BACKOFF
        for attempt in range(MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except botocore.exceptions.ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ("Throttling", "TooManyRequestsException", "RequestLimitExceeded"):
                    if attempt == MAX_RETRIES:
                        raise
                    logger.warning(
                        "Throttled on %s (attempt %d/%d), retrying in %.1fs",
                        func.__name__,
                        attempt + 1,
                        MAX_RETRIES,
                        backoff,
                    )
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise

    return wrapper
