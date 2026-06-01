"""Tests for ops_status_service."""
import pytest
from unittest.mock import MagicMock


class TestOpsStatusService:
    """Test cases for ops_status_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test ops status service can be initialized."""
        from app.services.ops_status_service import OpsStatusService
        service = OpsStatusService(db=mock_db)
        assert service is not None

    def test_get_status(self, mock_db):
        """Test getting ops status."""
        from app.services.ops_status_service import OpsStatusService
        mock_db.execute.return_value = {"status": "healthy"}
        service = OpsStatusService(db=mock_db)
        result = service.get_status()
        assert result["status"] == "healthy"
