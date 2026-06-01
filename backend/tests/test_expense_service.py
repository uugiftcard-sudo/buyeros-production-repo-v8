"""Tests for expense_service."""
import pytest
from unittest.mock import MagicMock


class TestExpenseService:
    """Test cases for expense_service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_expense_service_initialization(self, mock_db):
        """Test expense service can be initialized."""
        from app.services.expense_service import ExpenseService
        service = ExpenseService(db=mock_db)
        assert service is not None
        assert service.db == mock_db

    def test_create_expense(self, mock_db):
        """Test creating an expense."""
        from app.services.expense_service import ExpenseService
        mock_db.execute.return_value = {"id": 1, "amount": 100.0}
        service = ExpenseService(db=mock_db)
        result = service.create_expense(amount=100.0, description="Test")
        assert result["id"] == 1
        assert result["amount"] == 100.0

    def test_list_expenses(self, mock_db):
        """Test listing expenses."""
        from app.services.expense_service import ExpenseService
        mock_db.execute.return_value = [
            {"id": 1, "amount": 100.0, "status": "pending"},
            {"id": 2, "amount": 200.0, "status": "approved"},
        ]
        service = ExpenseService(db=mock_db)
        result = service.list_expenses()
        assert len(result) == 2
        assert result[0]["status"] == "pending"
        assert result[1]["status"] == "approved"

    def test_approve_expense(self, mock_db):
        """Test approving an expense."""
        from app.services.expense_service import ExpenseService
        mock_db.execute.return_value = {"id": 1, "status": "approved"}
        service = ExpenseService(db=mock_db)
        result = service.approve_expense(expense_id=1)
        assert result["status"] == "approved"

    def test_reject_expense(self, mock_db):
        """Test rejecting an expense."""
        from app.services.expense_service import ExpenseService
        mock_db.execute.return_value = {"id": 1, "status": "rejected"}
        service = ExpenseService(db=mock_db)
        result = service.reject_expense(expense_id=1, reason="Invalid")
        assert result["status"] == "rejected"

    def test_get_expense_by_id(self, mock_db):
        """Test getting expense by ID."""
        from app.services.expense_service import ExpenseService
        mock_db.execute.return_value = {"id": 1, "amount": 100.0}
        service = ExpenseService(db=mock_db)
        result = service.get_expense_by_id(expense_id=1)
        assert result["id"] == 1
        assert result["amount"] == 100.0
