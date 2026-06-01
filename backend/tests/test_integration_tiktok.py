"""Integration tests for TikTok connector."""
import pytest
from unittest.mock import patch, MagicMock


class TestTiktokIntegration:
    """Integration tests for TikTok API."""

    @pytest.fixture
    def tiktok_config(self):
        """Mock TikTok configuration."""
        return {
            "access_token": "test_token",
            "app_id": "test_app_id",
        }

    @pytest.mark.asyncio
    async def test_tiktok_connection(self, tiktok_config):
        """Test TikTok API connection."""
        from app.services.tiktok_connector import TiktokConnector
        
        connector = TiktokConnector(
            access_token=tiktok_config["access_token"],
            app_id=tiktok_config["app_id"],
        )
        
        # In mock mode, should return template data
        content = await connector.get_content()
        assert isinstance(content, list)

    @pytest.mark.asyncio
    async def test_tiktok_auth(self, tiktok_config):
        """Test TikTok authentication."""
        from app.services.tiktok_connector import TiktokConnector
        
        connector = TiktokConnector(
            access_token=tiktok_config["access_token"],
            app_id=tiktok_config["app_id"],
        )
        
        is_authenticated = connector._is_authenticated()
        assert isinstance(is_authenticated, bool)

    def test_tiktok_video_generation(self):
        """Test video content generation."""
        from app.services.tiktok_connector import TiktokConnector
        
        connector = TiktokConnector()
        
        # Test template generation
        video = connector._generate_template_video("test_script")
        assert "video_url" in video
        assert "thumbnail_url" in video
