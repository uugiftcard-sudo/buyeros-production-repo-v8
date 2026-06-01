"""Tests for shopify_connector service."""
import pytest
from unittest.mock import MagicMock


class TestShopifyConnector:
    """Test cases for shopify_connector service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        return MagicMock()

    def test_initialization(self, mock_db):
        """Test shopify connector can be initialized."""
        from app.services.shopify_connector import ShopifyConnector
        service = ShopifyConnector(db=mock_db)
        assert service is not None

    def test_get_products(self, mock_db):
        """Test getting products from Shopify."""
        from app.services.shopify_connector import ShopifyConnector
        mock_db.execute.return_value = {"products": [{"id": 1, "title": "Test Product"}]}
        service = ShopifyConnector(db=mock_db)
        result = service.get_products()
        assert "products" in result

    def test_sync_inventory(self, mock_db):
        """Test syncing inventory."""
        from app.services.shopify_connector import ShopifyConnector
        mock_db.execute.return_value = {"synced": 10}
        service = ShopifyConnector(db=mock_db)
        result = service.sync_inventory()
        assert "synced" in result
