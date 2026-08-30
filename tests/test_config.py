import os

from prsentinel.config import Config, write_default_config


def test_defaults_without_a_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = Config.load()
    assert config.provider == "groq"
    assert config.severity_threshold == "suggestion"
    assert "*.lock" in config.ignore


def test_loads_values_from_yaml_file(tmp_path):
    config_file = tmp_path / "custom.yml"
    config_file.write_text(
        "provider: gemini\nmodel: gemini-2.0-flash\nfail_on: warning\n",
        encoding="utf-8",
    )
    config = Config.load(str(config_file))
    assert config.provider == "gemini"
    assert config.model == "gemini-2.0-flash"
    assert config.fail_on == "warning"
    # Fields not present in the file keep their defaults
    assert config.max_files == 60


def test_write_default_config_creates_readable_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = write_default_config(".prsentinel.yml")
    assert path.exists()
    loaded = Config.load(str(path))
    assert loaded.provider == "groq"


def test_api_key_env_var_mapping():
    config = Config(provider="anthropic")
    assert config.api_key_env_var() == "ANTHROPIC_API_KEY"

    config = Config(provider="ollama")
    assert config.api_key_env_var() == ""


def test_resolved_api_key_reads_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    config = Config(provider="groq")
    assert config.resolved_api_key() == "test-key-123"
