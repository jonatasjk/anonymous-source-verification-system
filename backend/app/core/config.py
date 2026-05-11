from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import hashlib


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # PostgreSQL
    postgres_db: str = "asvs"
    postgres_user: str = "asvs"
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str

    # Platform identity (used in publication-ready attribution language)
    platform_name: str = "ASVS"

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    # gpt-4o context window is 128k tokens (~512k chars). 400k chars leaves
    # room for the system prompt and response tokens across any number of files.
    openai_max_chars_total: int = 400000

    # Storage
    storage_path: str = "storage"

    # TSA (FreeTSA.org — rotated March 2026, now EC P-384, valid to 2040)
    tsa_url: str = "https://freetsa.org/tsr"
    tsa_cert_generation: str = "2026-2040"
    tsa_cert_algorithm: str = "EC P-384 (secp384r1)"

    # OpenTimestamps calendar servers
    ots_calendar_urls: list[str] = [
        "https://alice.btc.calendar.opentimestamps.org",
        "https://bob.btc.calendar.opentimestamps.org",
        "https://finney.calendar.eternitywall.com",
    ]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def encryption_key(self) -> bytes:
        """Master AES-256 encryption key derived from SECRET_KEY."""
        return hashlib.sha256(self.secret_key.encode()).digest()


@lru_cache
def get_settings() -> Settings:
    return Settings()
