"""Tests for memory_timeline_service."""
import pytest
from unittest.mock import MagicMock


class TestMemoryTimelineService:
    """Test cases for memory_timeline_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test memory timeline service can be initialized."""
        from app.services.memory_timeline_service import MemoryTimelineService
        service = MemoryTimelineService(db=mock_db)
        assert service is not None

    def test_add_event(self, mock_db):
        """Test adding an event to the timeline."""
        from app.services.memory_timeline_service import MemoryTimelineService
        mock_db.execute.return_value = {"id": 1, "event": "test"}
        service = MemoryTimelineService(db=mock_db)
        result = service.add_event(event="test")
        assert "id" in result
