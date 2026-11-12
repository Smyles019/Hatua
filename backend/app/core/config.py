import hashlib

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "change-me"


class Settings(BaseSettings):
    """Read from environment variables or backend/.env (see .env.example)."""

    # postgresql+psycopg:// selects the psycopg 3 driver installed in requirements.txt
    database_url: str = "postgresql+psycopg://hatua:hatua_dev_password@localhost:5432/hatua"
    test_database_url: str = "postgresql+psycopg://hatua:hatua_dev_password@localhost:5432/hatua_test"
    jwt_secret: str = DEFAULT_SECRET
    access_token_hours: int = 12
    model_dir: str = "ml/artefacts"  # relative paths resolve from the repository root
    model_release: str = "1.1.0"     # folder under model_dir/release/
    # Under-24 model (hatua_ml.models.train_under2). If missing, 4-23 months fall back
    # to the WHO motor milestone check.
    under2_model_dir: str = "ml/artefacts/xgboost_under2/short_30"
    # Development only: serves the test UI at /test-ui and the /dev helper endpoints.
    # Must be false anywhere real people's data is stored.
    dev_mode: bool = False
    cors_origins: str = "*"          # comma-separated; tighten before deployment
    # Google sign-in: the OAuth "Web application" client ID(s) the app asks Google for
    # tokens with (serverClientId in the Flutter app). Comma-separated. Empty turns
    # Google sign-in off.
    google_client_ids: str = ""
    # Email (verification and password reset links). With SMTP_HOST empty nothing is
    # sent: the message is written to the server log instead, which is how the links
    # are read during development. Any SMTP provider works (Brevo, Resend, Gmail...).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "Hatua <no-reply@hatua.test>"
    # Address people's phones can open, used to build the links in emails.
    public_base_url: str = "http://localhost:8000"
    verify_link_hours: int = 48
    reset_link_minutes: int = 60

    @property
    def google_audiences(self) -> list[str]:
        return [c.strip() for c in self.google_client_ids.split(",") if c.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def check(self) -> None:
        """Refuse to start outside development with the placeholder or a short signing secret.

        In development a short secret is stretched with SHA-256 so it is long enough for
        HS256 and stays the same across restarts (sessions survive uvicorn --reload)."""
        if self.dev_mode:
            if len(self.jwt_secret) < 32:
                self.jwt_secret = hashlib.sha256(self.jwt_secret.encode()).hexdigest()
            return
        if self.jwt_secret.startswith(DEFAULT_SECRET) or len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be a random string of at least 32 characters "
                               "when DEV_MODE is false (see backend/.env.example)")


settings = Settings()
