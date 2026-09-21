import importlib
import app.config as config_module

def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    importlib.reload(config_module)
    assert config_module.settings.database_url == "postgresql://u:p@host:5432/db"
    assert config_module.settings.azure_openai_api_key == "azure-test-key"
    assert config_module.settings.azure_openai_endpoint == "https://example.openai.azure.com"
    assert config_module.settings.azure_openai_deployment == "gpt-4o"

def test_settings_validate_raises_without_key(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    importlib.reload(config_module)
    try:
        config_module.settings.validate()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
