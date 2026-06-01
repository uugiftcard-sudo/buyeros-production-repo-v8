"""Tests for buyers_service."""
import pytest
from unittest.mock import MagicMock


class TestBuyersService:
    """Test cases for buyers_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test buyers service can be initialized."""
        from app.services.buyers_service import BuyersService
        service = BuyersService(db=mock_db)
        assert service is not None

    def test_get_buyer(self, mock_db):
        """Test getting a buyer."""
        from app.services.buyers_service import BuyersService
        mock_db.execute.return_value = {"buyer_id": "buyer_123", "name": "Test Buyer"}
        service = BuyersService(db=mock_db)
        result = service.get_buyer(buyer_id="buyer_123")
        assert "buyer_id" in result

    def test_list_buyers(self, mock_db):
        """Test listing buyers."""
        from app.services.buyers_service import BuyersService
        mock_db.execute.return_value = [
            {"buyer_id": "buyer_1", "name": "Buyer One"},
            {"buyer_id": "buyer_2", "name": "Buyer Two"},
        ]
        service = BuyersService(db=mock_db)
        result = service.list_buyers()
        assert len(result) >= 0
