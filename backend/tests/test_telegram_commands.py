"""Tests for telegram_commands."""
import pytest
from unittest.mock import MagicMock, AsyncMock


class TestTelegramCommands:
    """Test cases for telegram_commands."""

    def test_telegram_commands_initialization(self):
        """Test telegram commands module loads."""
        from app.services.telegram_commands import TelegramCommands
        assert TelegramCommands is not None

    def test_parse_command(self):
        """Test parsing telegram command."""
        from app.services.telegram_commands import TelegramCommands
        cmd = TelegramCommands()
        result = cmd.parse("/start")
        assert result["command"] == "start"
