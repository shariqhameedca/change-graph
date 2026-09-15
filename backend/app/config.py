from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings parses .env into this module's own Settings fields, but
# it does NOT copy those values into the process environment. boto3 (and
# anything else that reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY /
# AWS_DEFAULT_REGION straight from os.environ) needs them there too, so
# .env is loaded into the real process environment here as well.
load_dotenv()


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://changegraph:changegraph@localhost:5432/changegraph"
    )

    llm_provider: str = "mock"
    aws_region: str = ""
    bedrock_model_id: str = ""

    engine_version: str = "1.0.0"

    # When true, compile jobs run synchronously (inline, before the compile
    # endpoint returns) instead of being scheduled as a background asyncio
    # task. Tests override the job-service dependency directly rather than
    # relying on this env var, exactly like the existing get_llm_provider
    # override -- this stays a plain dev/prod default.
    compile_jobs_eager: bool = False

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
