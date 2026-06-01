"""Tests for recon_store."""
import pytest
from unittest.mock import MagicMock


class TestReconStore:
    """Test cases for recon_store."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_recon_store_initialization(self, mock_db):
        """Test recon store can be initialized."""
        from app.services.recon_store import ReconStore
        store = ReconStore(db=mock_db)
        assert store is not None

    def test_save_reconciliation(self, mock_db):
        """Test saving reconciliation."""
        from app.services.recon_store import ReconStore
        mock_db.execute.return_value = {"id": 1, "status": "complete"}
        store = ReconStore(db=mock_db)
        result = store.save_reconciliation({})
        assert result["status"] == "complete"

    def test_get_reconciliation(self, mock_db):
        """Test getting reconciliation."""
        from app.services.recon_store import ReconStore
        mock_db.execute.return_value = {"id": 1, "amount": 500.0}
        store = ReconStore(db=mock_db)
        result = store.get_reconciliation(recon_id=1)
        assert result["id"] == 1
