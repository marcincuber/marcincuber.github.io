"""Bounded HTTP requests for explicit maintenance commands, never site builds."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class FetchError(ValueError):
    """An HTTP check failed after its retry budget."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def retry_delay(value: str | None, attempt: int) -> float:
    """Honor Retry-After seconds or HTTP dates, with a 30-second wait ceiling."""
    try:
        if value is None:
            raise ValueError("no Retry-After")
        delay = float(value)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            delay = 2 ** attempt
    return max(0, min(delay, 30))


def fetch(
    url: str, *, max_bytes: int | None = 5 * 1024 * 1024,
    attempts: int = 3, timeout: int = 30,
) -> bytes:
    """GET with backoff; max_bytes=None checks status without downloading the body."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        delay = retry_delay(None, attempt + 1)
        try:
            request = Request(url, headers={
                "User-Agent": "marcincuber-portfolio/1.0 (+https://marcincuber.github.io)",
                "Accept": "*/*",
                "Cache-Control": "no-cache",
            })
            with urlopen(request, timeout=timeout) as response:
                payload = response.read(max_bytes + 1) if max_bytes is not None else b""
            if max_bytes is not None and len(payload) > max_bytes:
                raise FetchError(f"response exceeds the {max_bytes}-byte size limit")
            return payload
        except HTTPError as error:
            failure = FetchError(f"HTTP {error.code}: {error.reason}", status=error.code)
            delay = retry_delay(error.headers.get("Retry-After"), attempt + 1)
            error.close()
            if error.code not in {408, 429} and not 500 <= error.code <= 599:
                raise failure from error
        except (OSError, HTTPException) as error:
            failure = FetchError(str(error))
        except ValueError as error:
            if isinstance(error, FetchError):
                raise
            raise FetchError(str(error)) from error
        if attempt == attempts - 1:
            raise failure
        print(f"Request failed ({failure}); retrying in {delay:g}s "
              f"({attempt + 2}/{attempts}).", file=sys.stderr)
        time.sleep(delay)
    raise AssertionError("unreachable")
