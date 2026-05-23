"""Unit tests for src/config.py."""


from src.config import (
    Settings,
    get_delay,
    get_http_timeout,
    get_log_level,
    get_max_retries,
    get_output_dir,
    get_rate_limit,
    get_settings,
    get_user_agents,
    get_yaml_value,
)


class TestGetSettings:
    def test_get_settings_returns_singleton(self):
        """Calling get_settings() twice returns the same instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_defaults(self):
        """Settings have sensible defaults without env vars."""
        s = Settings()  # fresh instance bypasses singleton
        assert isinstance(s.output_dir, str)
        assert isinstance(s.default_delay, float)
        assert isinstance(s.max_retries, int)
        assert s.log_level == "INFO"

    def test_settings_env_override(self, monkeypatch):
        """Environment variables are read with the SCAPERS_ prefix."""
        monkeypatch.setenv("SCAPERS_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("SCAPERS_DEFAULT_DELAY", "5.0")
        s = Settings()
        assert s.log_level == "DEBUG"
        assert s.default_delay == 5.0


class TestGetDelay:
    def test_get_delay_returns_float(self):
        """get_delay returns a numeric value."""
        result = get_delay("amazon")
        assert isinstance(result, float)

    def test_get_delay_unknown_scraper_falls_back_to_default(self):
        """Unknown scraper names fall back to the default delay."""
        result = get_delay("nonexistent_scraper_xyz")
        assert isinstance(result, float)
        assert result >= 0


class TestGetRateLimit:
    def test_get_rate_limit_returns_int(self):
        """get_rate_limit returns an integer RPM."""
        result = get_rate_limit("amazon")
        assert isinstance(result, int)
        assert result > 0


class TestGetHttpTimeout:
    def test_get_http_timeout_returns_int(self):
        """get_http_timeout returns a positive integer."""
        result = get_http_timeout()
        assert isinstance(result, int)
        assert result > 0


class TestGetLogLevel:
    def test_get_log_level_returns_str(self):
        """get_log_level returns a non-empty string."""
        result = get_log_level()
        assert isinstance(result, str)
        assert result


class TestGetMaxRetries:
    def test_get_max_retries_returns_int(self):
        """get_max_retries returns a positive integer."""
        result = get_max_retries()
        assert isinstance(result, int)
        assert result >= 1


class TestGetOutputDir:
    def test_get_output_dir_returns_path(self):
        """get_output_dir returns a Path object."""
        from pathlib import Path

        result = get_output_dir()
        assert isinstance(result, Path)


class TestGetUserAgents:
    def test_get_user_agents_returns_list(self):
        """get_user_agents returns a list, never empty."""
        result = get_user_agents()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(ua, str) for ua in result)


class TestGetYamlValue:
    def test_get_yaml_value_found(self):
        """get_yaml_value returns the value when keys match."""
        # rate_limits is a top-level key in config.yaml
        result = get_yaml_value("rate_limits")
        assert result is not None

    def test_get_yaml_value_missing_returns_default(self):
        """get_yaml_value returns the default for missing keys."""
        result = get_yaml_value("nonexistent", "deep", default="fallback")
        assert result == "fallback"

    def test_get_yaml_value_nested(self):
        """get_yaml_value traverses nested keys correctly."""
        result = get_yaml_value("delays", "default")
        # Should be a numeric value if delays.default exists
        assert result is not None
