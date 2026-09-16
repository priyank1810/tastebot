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
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    def validate(self) -> None:
        if not self.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")


settings = Settings()
