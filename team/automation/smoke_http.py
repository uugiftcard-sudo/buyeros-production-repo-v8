#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass


DEFAULTS = {
    "buyeros": "http://127.0.0.1:3000",
    "xau": "http://127.0.0.1:3002",
    "cloth": "http://127.0.0.1:3001",
}


@dataclass(frozen=True)
class Check:
    path: str
    label: str
    contains: tuple[str, ...] = ()
    json_keys: tuple[str, ...] = ()


SCENARIOS = {
    "buyeros": [
        Check("/", "dashboard shell"),
        Check("/#ops", "ops anchor"),
    ],
    "xau": [
        Check("/", "dashboard", contains=("XAU",)),
        Check("/stream/obs-scene.html", "OBS scene"),
        Check("/health", "server health", json_keys=("status",)),
    ],
    "cloth": [
        Check("/api/health", "API health", json_keys=("success",)),
        Check("/api/live/readiness", "live readiness"),
        Check("/api/products?limit=3", "products pagination"),
        Check("/api/support/faqs", "support faqs"),
    ],
}


def fetch(url: str, timeout: float) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "team-automation-smoke/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(200_000).decode("utf-8", errors="replace")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read(20_000).decode("utf-8", errors="replace")
        return exc.code, body


def assert_check(base_url: str, check: Check, timeout: float) -> str:
    url = base_url.rstrip("/") + check.path
    status, body = fetch(url, timeout)
    if status < 200 or status >= 400:
        raise AssertionError(f"{check.label}: HTTP {status} {url}")
    for needle in check.contains:
        if needle not in body:
            raise AssertionError(f"{check.label}: missing text {needle!r}")
    if check.json_keys:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"{check.label}: invalid JSON") from exc
        for key in check.json_keys:
            if key not in parsed:
                raise AssertionError(f"{check.label}: missing JSON key {key!r}")
    return f"PASS {check.label}: {url}"


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP smoke checks for team automation")
    parser.add_argument("repo", choices=sorted(SCENARIOS))
    parser.add_argument("--base-url")
    parser.add_argument("--timeout", type=float, default=float(os.getenv("TEAM_AUTOMATION_HTTP_TIMEOUT", "5")))
    args = parser.parse_args()

    env_name = f"TEAM_AUTOMATION_{args.repo.upper()}_URL"
    base_url = args.base_url or os.getenv(env_name) or DEFAULTS[args.repo]
    failures: list[str] = []
    for check in SCENARIOS[args.repo]:
        try:
            print(assert_check(base_url, check, args.timeout))
        except Exception as exc:
            failures.append(str(exc))

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
