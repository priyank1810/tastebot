import importlib
import app.config as config_module

def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    importlib.reload(config_module)
    assert config_module.settings.database_url == "postgresql://u:p@host:5432/db"
    assert config_module.settings.anthropic_api_key == "sk-test"

def test_settings_validate_raises_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    importlib.reload(config_module)
    try:
        config_module.settings.validate()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
