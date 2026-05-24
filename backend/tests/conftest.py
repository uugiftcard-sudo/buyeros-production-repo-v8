"""Pytest configuration for BuyerOS tests.

Sets BUYEROS_ENV=test so that the rate limiter middleware skips enforcement
during test runs (tests handle their own auth/key scenarios).
"""
import os
os.environ.setdefault("BUYEROS_ENV", "test")
