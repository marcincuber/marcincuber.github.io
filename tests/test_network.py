"""Deterministic HTTP retry checks without network calls or actual waits."""

from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import format_datetime
from http.client import IncompleteRead
import io
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from portfolio_site.network import FetchError, fetch, retry_delay


def response(payload: bytes = b"success") -> MagicMock:
    result = MagicMock()
    result.__enter__.return_value.read.return_value = payload
    return result


def http_error(status: int, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://example.com/", status, "error", headers, io.BytesIO())


class NetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        sleeper = patch("portfolio_site.network.time.sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def test_retries_transient_http_and_network_errors(self) -> None:
        for error in (http_error(429, "7"), http_error(503), http_error(408),
                      URLError("temporary DNS failure"), TimeoutError(), IncompleteRead(b"")):
            with self.subTest(error=error), patch("portfolio_site.network.urlopen",
                                                 side_effect=[error, response()]) as request:
                self.assertEqual(fetch("https://example.com/"), b"success")
                self.assertEqual(request.call_count, 2)
        self.sleep.assert_any_call(7)

    def test_permanent_http_errors_are_not_retried(self) -> None:
        for status in (400, 401, 403, 404, 410):
            with self.subTest(status=status), patch("portfolio_site.network.urlopen",
                                                    side_effect=http_error(status)) as request:
                with self.assertRaises(FetchError) as caught:
                    fetch("https://example.com/")
                self.assertEqual(caught.exception.status, status)
                request.assert_called_once()
        self.sleep.assert_not_called()

    def test_retry_budget_and_backoff_are_bounded(self) -> None:
        with patch("portfolio_site.network.urlopen", side_effect=URLError("offline")) as request:
            with self.assertRaises(FetchError):
                fetch("https://example.com/")
        self.assertEqual(request.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 4])

    def test_retry_after_handles_dates_invalid_values_and_wait_ceiling(self) -> None:
        future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=15))
        self.assertGreater(retry_delay(future, 1), 12)
        self.assertLessEqual(retry_delay(future, 1), 15)
        self.assertEqual(retry_delay("broken", 2), 4)
        self.assertEqual(retry_delay("600", 1), 30)
        self.assertEqual(retry_delay("-10", 1), 0)

    def test_oversized_response_is_not_retried(self) -> None:
        with patch("portfolio_site.network.urlopen", return_value=response(b"too long")) as request:
            with self.assertRaisesRegex(FetchError, "size limit"):
                fetch("https://example.com/", max_bytes=3)
            request.assert_called_once()

    def test_link_probe_does_not_read_a_large_body(self) -> None:
        result = response()
        with patch("portfolio_site.network.urlopen", return_value=result):
            self.assertEqual(fetch("https://example.com/", max_bytes=None), b"")
        result.__enter__.return_value.read.assert_not_called()
