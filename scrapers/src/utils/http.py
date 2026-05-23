"""
HTTP client with retry logic, User-Agent rotation, and proxy support.

Wraps httpx for synchronous use with tenacity-powered retries.
"""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING, Any

import httpx
import requests
from tenacity import (
    RetryCallState,
    Retrying,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_http_timeout, get_max_retries, get_user_agents

if TYPE_CHECKING:
    pass

_LOG_TEMPLATE = "httpx request failed [attempt {attempt}/{max_retries}]: {sleep}s backoff"

# ─── Sentinel to detect blocked responses ────────────────────────
_BLOCKED_STATUS_CODES = {403, 429, 499, 999}


def _build_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return headers dict with a randomly-selected User-Agent."""
    base = {
        "User-Agent": random.choice(get_user_agents()),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if extra:
        base.update(extra)
    return base


def _is_blocked(resp: httpx.Response | requests.Response) -> bool:
    """Return True if the response indicates a block/bot-detect."""
    status = getattr(resp, "status_code", 0)
    if status in _BLOCKED_STATUS_CODES:
        return True
    # Also check for captcha / block page signatures
    text = getattr(resp, "text", "")[:500].lower()
    blocked_phrases = ["captcha", "access denied", "blocked", "please verify you are a robot"]
    return any(p in text for p in blocked_phrases)


def _retry_callback(retry_state: RetryCallState) -> None:
    """Log each retry attempt."""
    import logging

    log = logging.getLogger("scrapers.http")
    attempt = retry_state.attempt_number
    wait = retry_state.next_action.sleep if retry_state.next_action else 0
    log.warning(f"[attempt {attempt}] request failed, backing off {wait:.1f}s")


def http_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    proxies: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> requests.Response | None:
    """
    Perform a GET request with automatic retry and backoff.

    Args:
        url: Target URL
        params: Query string parameters
        headers: Additional headers (UA is always injected)
        timeout: Request timeout in seconds
        max_retries: Max retry attempts (default from config)
        proxies: HTTP/HTTPS proxy dict
        extra_headers: Alias for headers

    Returns:
        requests.Response on success, None on final failure.
    """
    timeout = timeout or get_http_timeout()
    max_retries = max_retries or get_max_retries()
    final_headers = _build_headers(headers or extra_headers or {})

    for attempt in Retrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=(
            lambda rc: (
                isinstance(rc.outcome.exception(), requests.RequestException)
                or (
                    hasattr(rc.outcome, "result")
                    and rc.outcome.result() is not None
                    and _is_blocked(rc.outcome.result())
                )
            )
        ),
        before_sleep=before_sleep_log(logging.getLogger("scrapers.http"), logging.WARNING),
        reraise=True,
    ):
        with attempt:
            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers=final_headers,
                    timeout=timeout,
                    proxies=proxies,
                    allow_redirects=True,
                )
                if _is_blocked(resp):
                    # Exponential backoff for blocked responses
                    backoff = random.uniform(5, 15)
                    import logging

                    logging.getLogger("scrapers.http").warning(
                        f"Blocked ({resp.status_code}), sleeping {backoff:.0f}s"
                    )
                    time.sleep(backoff)
                    raise requests.RequestException(f"Blocked: {resp.status_code}")
                return resp
            except requests.RequestException as exc:
                import logging

                log = logging.getLogger("scrapers.http")
                if attempt.retry_state.attempt_number < max_retries:
                    wait = min(2**attempt.retry_state.attempt_number, 30)
                    log.debug(f"Request failed: {exc}, retrying in {wait}s")
                raise

    return None


def http_post(
    url: str,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    proxies: dict[str, str] | None = None,
) -> requests.Response | None:
    """
    Perform a POST request with automatic retry and backoff.
    """
    timeout = timeout or get_http_timeout()
    max_retries = max_retries or get_max_retries()
    final_headers = _build_headers(headers or {})

    for attempt in Retrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        before_sleep=before_sleep_log(logging.getLogger("scrapers.http"), logging.WARNING),
        reraise=True,
    ):
        with attempt:
            try:
                return requests.post(
                    url,
                    json=json,
                    data=data,
                    headers=final_headers,
                    timeout=timeout,
                    proxies=proxies,
                )
            except requests.RequestException:
                raise

    return None
