"""Tests for task_dispatcher_service."""
import pytest
from unittest.mock import MagicMock


class TestTaskDispatcherService:
    """Test cases for task_dispatcher_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test task dispatcher can be initialized."""
        from app.services.task_dispatcher_service import TaskDispatcherService
        service = TaskDispatcherService(db=mock_db)
        assert service is not None

    def test_dispatch_task(self, mock_db):
        """Test dispatching a task."""
        from app.services.task_dispatcher_service import TaskDispatcherService
        mock_db.execute.return_value = {"task_id": "task_123", "status": "dispatched"}
        service = TaskDispatcherService(db=mock_db)
        result = service.dispatch_task(task={"type": "test"})
        assert "task_id" in result
        assert result["status"] == "dispatched"

    def test_get_task_status(self, mock_db):
        """Test getting task status."""
        from app.services.task_dispatcher_service import TaskDispatcherService
        mock_db.execute.return_value = {"task_id": "task_123", "status": "running"}
        service = TaskDispatcherService(db=mock_db)
        result = service.get_task_status(task_id="task_123")
        assert result["task_id"] == "task_123"

    def test_cancel_task(self, mock_db):
        """Test cancelling a task."""
        from app.services.task_dispatcher_service import TaskDispatcherService
        mock_db.execute.return_value = {"task_id": "task_123", "status": "cancelled"}
        service = TaskDispatcherService(db=mock_db)
        result = service.cancel_task(task_id="task_123")
        assert result["status"] == "cancelled"

    def test_list_pending_tasks(self, mock_db):
        """Test listing pending tasks."""
        from app.services.task_dispatcher_service import TaskDispatcherService
        mock_db.execute.return_value = [
            {"task_id": "task_1", "status": "pending"},
            {"task_id": "task_2", "status": "pending"},
        ]
        service = TaskDispatcherService(db=mock_db)
        result = service.list_pending_tasks()
        assert len(result) == 2

    def test_retry_task(self, mock_db):
        """Test retrying a failed task."""
        from app.services.task_dispatcher_service import TaskDispatcherService
        mock_db.execute.return_value = {"task_id": "task_123", "status": "pending", "retries": 1}
        service = TaskDispatcherService(db=mock_db)
        result = service.retry_task(task_id="task_123")
        assert "retries" in result
