"""Tests for cloth_integration service."""
import pytest
from unittest.mock import MagicMock


class TestCLOTHIntegration:
    """Test cases for cloth_integration service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_cloth_integration_initialization(self, mock_db):
        """Test CLOTH integration can be initialized."""
        from app.services.cloth_integration import CLOTHIntegration
        service = CLOTHIntegration(db=mock_db)
        assert service is not None

    def test_sync_data(self, mock_db):
        """Test syncing data from CLOTH."""
        from app.services.cloth_integration import CLOTHIntegration
        mock_db.execute.return_value = {"synced": 10}
        service = CLOTHIntegration(db=mock_db)
        result = service.sync_data()
        assert result["synced"] >= 0
