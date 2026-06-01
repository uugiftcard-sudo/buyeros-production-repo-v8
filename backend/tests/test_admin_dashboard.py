"""Tests for admin_dashboard service."""
import pytest
from unittest.mock import MagicMock


class TestAdminDashboard:
    """Test cases for admin_dashboard service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test admin dashboard can be initialized."""
        from app.services.admin_dashboard import AdminDashboard
        service = AdminDashboard(db=mock_db)
        assert service is not None

    def test_get_stats(self, mock_db):
        """Test getting dashboard statistics."""
        from app.services.admin_dashboard import AdminDashboard
        mock_db.execute.return_value = {"total": 100, "active": 50}
        service = AdminDashboard(db=mock_db)
        result = service.get_stats()
        assert "total" in result

    def test_render_table_card(self, mock_db):
        """Test rendering a table card."""
        from app.services.admin_dashboard import AdminDashboard
        service = AdminDashboard(db=mock_db)
        result = service.render_table_card(
            title="Test",
            headers=["ID", "Name"],
            rows=[["1", "Test"]],
        )
        assert "Test" in result
        assert "<table" in result or "<section" in result

    def test_get_recent_activity(self, mock_db):
        """Test getting recent activity."""
        from app.services.admin_dashboard import AdminDashboard
        mock_db.execute.return_value = [
            {"action": "task_created", "timestamp": "2026-01-01"},
        ]
        service = AdminDashboard(db=mock_db)
        result = service.get_recent_activity()
        assert isinstance(result, list)
