"""Tests for receipt_vision_service."""
import pytest
from unittest.mock import MagicMock


class TestReceiptVisionService:
    """Test cases for receipt_vision_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test receipt vision service can be initialized."""
        from app.services.receipt_vision_service import ReceiptVisionService
        service = ReceiptVisionService(db=mock_db)
        assert service is not None

    def test_process_receipt(self, mock_db):
        """Test processing a receipt image."""
        from app.services.receipt_vision_service import ReceiptVisionService
        mock_db.execute.return_value = {"extracted": {"amount": 100.0}}
        service = ReceiptVisionService(db=mock_db)
        result = service.process_receipt(image_data=b"fake_image_data")
        assert "extracted" in result
