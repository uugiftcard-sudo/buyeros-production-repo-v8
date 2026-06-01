"""Tests for tiktok_connector."""
import pytest
from unittest.mock import MagicMock


class TestTiktokConnector:
    """Test cases for tiktok_connector."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test TikTok connector can be initialized."""
        from app.services.tiktok_connector import TiktokConnector
        service = TiktokConnector(db=mock_db)
        assert service is not None

    def test_get_content(self, mock_db):
        """Test getting content from TikTok."""
        from app.services.tiktok_connector import TiktokConnector
        mock_db.execute.return_value = {"content": []}
        service = TiktokConnector(db=mock_db)
        result = service.get_content()
        assert "content" in result or isinstance(result, list)
