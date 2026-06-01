"""Tests for bank_import_service."""
import pytest
from unittest.mock import MagicMock


class TestBankImportService:
    """Test cases for bank_import_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_bank_import_service_initialization(self, mock_db):
        """Test bank import service can be initialized."""
        from app.services.bank_import_service import BankImportService
        service = BankImportService(db=mock_db)
        assert service is not None

    def test_import_transactions(self, mock_db):
        """Test importing bank transactions."""
        from app.services.bank_import_service import BankImportService
        mock_db.execute.return_value = {"imported": 10, "skipped": 2}
        service = BankImportService(db=mock_db)
        result = service.import_transactions([])
        assert result["imported"] == 10
        assert result["skipped"] == 2
