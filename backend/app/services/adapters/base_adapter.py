"""Abstract base for payment provider adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PaymentAdapter(ABC):
    """Abstract base for payment provider adapters."""

    @abstractmethod
    def configured(self) -> bool:
        """Return True if this adapter has the required credentials."""
        ...

    @abstractmethod
    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a refund and return a provider-specific result dict."""
        ...
