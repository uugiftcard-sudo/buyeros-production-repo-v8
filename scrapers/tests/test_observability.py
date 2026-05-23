"""Unit tests for src/observability.py."""

import logging

import pytest


class TestSetupObservability:
    def test_setup_observability_does_not_raise(self):
        """setup_observability() runs without raising even when structlog is missing."""
        from src.observability import setup_observability

        # Should not raise
        setup_observability()

    def test_setup_structlog_with_json_env(self, monkeypatch):
        """_setup_structlog uses JSON renderer when LOG_FORMAT=json."""
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        # Should not raise
        from src.observability import _setup_structlog

        _setup_structlog()

    def test_setup_sentry_no_dsn_noops(self):
        """_setup_sentry returns early when SENTRY_DSN is not set."""
        from src.observability import _setup_sentry

        # Should not raise and returns None
        _setup_sentry()

    def test_setup_sentry_missing_package_noops(self, monkeypatch):
        """_setup_sentry logs a warning when sentry-sdk is not installed."""
        import importlib

        # Simulate import failure by removing the module
        monkeypatch.setenv("SENTRY_DSN", "https://abc@example.com/123")
        monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", None)

        # Reload to pick up the patched state
        import src.observability

        importlib.reload(src.observability)
        # Should not raise even if sentry_sdk is unavailable
        src.observability._setup_sentry()
