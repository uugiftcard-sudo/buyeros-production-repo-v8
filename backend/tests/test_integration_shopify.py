"""Integration tests for Shopify connector."""
import pytest
from unittest.mock import patch, MagicMock


class TestShopifyIntegration:
    """Integration tests for Shopify API."""

    @pytest.fixture
    def shopify_config(self):
        """Mock Shopify configuration."""
        return {
            "api_key": "test_key",
            "store_url": "https://test-store.myshopify.com",
            "access_token": "test_token",
        }

    @pytest.mark.asyncio
    async def test_shopify_connection(self, shopify_config):
        """Test Shopify API connection."""
        from app.services.shopify_connector import ShopifyConnector
        
        connector = ShopifyConnector(
            api_key=shopify_config["api_key"],
            store_url=shopify_config["store_url"],
            access_token=shopify_config["access_token"],
        )
        
        # In mock mode, should return empty results
        products = await connector.list_products(limit=5)
        assert isinstance(products, list)

    @pytest.mark.asyncio
    async def test_shopify_create_product(self, shopify_config):
        """Test creating a product."""
        from app.services.shopify_connector import ShopifyConnector
        
        connector = ShopifyConnector(
            api_key=shopify_config["api_key"],
            store_url=shopify_config["store_url"],
            access_token=shopify_config["access_token"],
        )
        
        product_data = {
            "title": "Test Product",
            "price": 99.99,
            "sku": "TEST-001",
        }
        
        result = await connector.create_product(product_data)
        assert "id" in result or "mock_id" in result

    def test_shopify_validation(self):
        """Test input validation."""
        from app.services.shopify_connector import ShopifyConnector
        
        connector = ShopifyConnector()
        
        # Test price validation
        assert connector._validate_price(100.0) == 100.0
        assert connector._validate_price(-10.0) is None
        
        # Test SKU validation
        assert connector._validate_sku("SKU-001") == "SKU-001"
        assert connector._validate_sku("") is None
