"""Integration tests for Supabase client."""
import pytest
from unittest.mock import patch, AsyncMock


class TestSupabaseIntegration:
    """Integration tests for Supabase client."""

    @pytest.fixture
    def supabase_client(self):
        """Create Supabase client."""
        from app.supabase import SupabaseClient
        return SupabaseClient(
            url="https://test.supabase.co",
            key="test_key",
        )

    def test_client_configuration(self, supabase_client):
        """Test client is properly configured."""
        assert supabase_client.configured is True
        assert supabase_client.url == "https://test.supabase.co"

    def test_headers_generation(self, supabase_client):
        """Test API headers."""
        headers = supabase_client.get_headers()
        assert "apikey" in headers
        assert "Authorization" in headers
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_query_unconfigured(self, supabase_client):
        """Test query when not configured."""
        # Reset to unconfigured
        supabase_client.key = ""
        result = await supabase_client.query("test_table")
        assert result == []

    def test_singleton_pattern(self):
        """Test singleton instance."""
        from app.supabase import SupabaseClient
        
        SupabaseClient.reset_instance()
        instance1 = SupabaseClient.get_instance()
        instance2 = SupabaseClient.get_instance()
        
        assert instance1 is instance2
        
        SupabaseClient.reset_instance()

    @pytest.mark.asyncio
    async def test_insert_unconfigured(self, supabase_client):
        """Test insert when not configured."""
        supabase_client.key = ""
        result = await supabase_client.insert("test_table", {"key": "value"})
        assert "error" in result
