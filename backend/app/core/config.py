from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables or backend/.env (see .env.example)."""

    # postgresql+psycopg:// selects the psycopg 3 driver installed in requirements.txt
    database_url: str = "postgresql+psycopg://hatua:hatua_dev_password@localhost:5432/hatua"
    test_database_url: str = "postgresql+psycopg://hatua:hatua_dev_password@localhost:5432/hatua_test"
    jwt_secret: str = "change-me"
    model_dir: str = "ml/artefacts"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
