from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://hatua:password@localhost:5432/hatua"
    jwt_secret: str = "change-me"
    model_dir: str = "ml/artefacts"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
