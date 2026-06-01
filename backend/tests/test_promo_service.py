"""Tests for promo_service."""
import pytest
from unittest.mock import MagicMock


class TestPromoService:
    """Test cases for promo_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test promo service can be initialized."""
        from app.services.promo_service import PromoService
        service = PromoService(db=mock_db)
        assert service is not None

    def test_get_promo(self, mock_db):
        """Test getting a promo."""
        from app.services.promo_service import PromoService
        mock_db.execute.return_value = {"promo_id": "promo_123", "code": "TEST10"}
        service = PromoService(db=mock_db)
        result = service.get_promo(promo_id="promo_123")
        assert "promo_id" in result

    def test_validate_promo_code(self, mock_db):
        """Test validating a promo code."""
        from app.services.promo_service import PromoService
        mock_db.execute.return_value = {"valid": True, "discount": 10.0}
        service = PromoService(db=mock_db)
        result = service.validate_promo_code(code="TEST10")
        assert "valid" in result
