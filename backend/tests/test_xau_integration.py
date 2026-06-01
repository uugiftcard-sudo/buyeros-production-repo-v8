"""Tests for xau_integration service."""
import pytest
from unittest.mock import MagicMock


class TestXAUIntegration:
    """Test cases for xau_integration service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_xau_integration_initialization(self, mock_db):
        """Test XAU integration can be initialized."""
        from app.services.xau_integration import XAUIntegration
        service = XAUIntegration(db=mock_db)
        assert service is not None

    def test_get_prices(self, mock_db):
        """Test getting XAU prices."""
        from app.services.xau_integration import XAUIntegration
        mock_db.execute.return_value = {"prices": [{"symbol": "XAU", "price": 2000.0}]}
        service = XAUIntegration(db=mock_db)
        result = service.get_prices()
        assert result["prices"][0]["symbol"] == "XAU"
