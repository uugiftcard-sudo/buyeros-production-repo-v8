"""Tests for finance_service."""
import pytest
from unittest.mock import MagicMock


class TestFinanceService:
    """Test cases for finance_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_finance_service_initialization(self, mock_db):
        """Test finance service can be initialized."""
        from app.services.finance_service import FinanceService
        service = FinanceService(db=mock_db)
        assert service is not None

    def test_get_balance(self, mock_db):
        """Test getting balance."""
        from app.services.finance_service import FinanceService
        mock_db.execute.return_value = {"balance": 1000.0}
        service = FinanceService(db=mock_db)
        result = service.get_balance()
        assert result["balance"] == 1000.0

    def test_get_transactions(self, mock_db):
        """Test getting transactions."""
        from app.services.finance_service import FinanceService
        mock_db.execute.return_value = [
            {"id": 1, "type": "credit", "amount": 500.0},
            {"id": 2, "type": "debit", "amount": 100.0},
        ]
        service = FinanceService(db=mock_db)
        result = service.get_transactions()
        assert len(result) == 2
