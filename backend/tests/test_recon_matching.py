"""Tests for recon_matching."""
import pytest
from unittest.mock import MagicMock


class TestReconMatching:
    """Test cases for recon_matching."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test recon matching can be initialized."""
        from app.services.recon_matching import ReconMatching
        service = ReconMatching(db=mock_db)
        assert service is not None

    def test_match_transactions(self, mock_db):
        """Test matching transactions."""
        from app.services.recon_matching import ReconMatching
        mock_db.execute.return_value = {"matched": 5, "unmatched": 2}
        service = ReconMatching(db=mock_db)
        result = service.match_transactions([])
        assert "matched" in result
