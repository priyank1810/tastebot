import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.database_url = os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/restaurants"
        )
        self.test_database_url = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5433/restaurants_test",
        )
        self.azure_openai_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        self.azure_openai_api_version = os.environ.get(
            "AZURE_OPENAI_API_VERSION", "2024-10-21"
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in [
                ("AZURE_OPENAI_API_KEY", self.azure_openai_api_key),
                ("AZURE_OPENAI_ENDPOINT", self.azure_openai_endpoint),
                ("AZURE_OPENAI_DEPLOYMENT", self.azure_openai_deployment),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(f"missing required env vars: {', '.join(missing)}")


settings = Settings()
