import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

if APP_ENV not in {"development", "test", "production"}:
    raise RuntimeError("APP_ENV must be development, test, or production")

if APP_ENV != "production":
    load_dotenv(BACKEND_DIR / ".env", override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    APP_ENV: str = APP_ENV
    OPENAI_API_KEY: str
    DATABASE_URL: str
    DEMO_TARGET_URL: str | None = None
    FRONTEND_ORIGINS: str | None = None
    GITHUB_TOKEN: str | None = None
    SEARCH_PROVIDER: str = "exa"
    EXA_API_KEY: str | None = None
    EXA_SEARCH_RESULT_COUNT: int = 10
    BRAVE_SEARCH_API_KEY: str | None = None
    BRAVE_SEARCH_RESULT_COUNT: int = 10
    GOOGLE_SEARCH_API_KEY: str | None = None
    GOOGLE_SEARCH_ENGINE_ID: str | None = None
    REDDIT_USERNAME: str | None = None
    REDDIT_PASSWORD: str | None = None
    PUBLISH_DRY_RUN: bool = True
    ACCOUNT_ID: int | None = None
    AGENT_NAME: str | None = None
    BACKEND_URL: str = "http://localhost:8000"
    XIAOHONGSHU_RETRIEVAL_COMMAND: str | None = None
    XIAOHONGSHU_RETRIEVAL_TIMEOUT_SECONDS: int = 180
    XIAOHONGSHU_RETRIEVAL_LIMIT: int = 20
    WEBSITE_AUDIT_MAX_PAGES: int = 200
    WEBSITE_AUDIT_CANDIDATE_PAGES: int = 150
    WEBSITE_AUDIT_SAMPLE_PAGES: int = 30
    WEBSITE_AUDIT_BROWSER_FALLBACK_ENABLED: bool = True
    WEBSITE_AUDIT_BROWSER_CONCURRENCY: int = 2
    WEBSITE_AUDIT_BROWSER_TIMEOUT_MS: int = 10_000
    WEBSITE_AUDIT_BROWSER_FALLBACK_LIMIT: int = 10

    @model_validator(mode="after")
    def validate_environment_contract(self):
        environment = self.APP_ENV.strip().lower()
        if environment not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        self.APP_ENV = environment

        if self.WEBSITE_AUDIT_MAX_PAGES < 1:
            raise ValueError("WEBSITE_AUDIT_MAX_PAGES must be at least 1")
        if self.WEBSITE_AUDIT_SAMPLE_PAGES < 1:
            raise ValueError("WEBSITE_AUDIT_SAMPLE_PAGES must be at least 1")
        if self.WEBSITE_AUDIT_CANDIDATE_PAGES < 1:
            raise ValueError("WEBSITE_AUDIT_CANDIDATE_PAGES must be at least 1")
        if self.WEBSITE_AUDIT_CANDIDATE_PAGES < self.WEBSITE_AUDIT_SAMPLE_PAGES:
            raise ValueError(
                "WEBSITE_AUDIT_CANDIDATE_PAGES must be at least WEBSITE_AUDIT_SAMPLE_PAGES"
            )
        if self.WEBSITE_AUDIT_BROWSER_CONCURRENCY < 1:
            raise ValueError("WEBSITE_AUDIT_BROWSER_CONCURRENCY must be at least 1")
        if self.WEBSITE_AUDIT_BROWSER_TIMEOUT_MS < 250:
            raise ValueError("WEBSITE_AUDIT_BROWSER_TIMEOUT_MS must be at least 250")
        if self.WEBSITE_AUDIT_BROWSER_FALLBACK_LIMIT < 1:
            raise ValueError("WEBSITE_AUDIT_BROWSER_FALLBACK_LIMIT must be at least 1")
        self.SEARCH_PROVIDER = self.SEARCH_PROVIDER.strip().lower()
        if self.SEARCH_PROVIDER not in {"exa", "brave", "google"}:
            raise ValueError("SEARCH_PROVIDER must be exa, brave, or google")
        if not 1 <= self.EXA_SEARCH_RESULT_COUNT <= 100:
            raise ValueError("EXA_SEARCH_RESULT_COUNT must be between 1 and 100")
        if not 1 <= self.BRAVE_SEARCH_RESULT_COUNT <= 20:
            raise ValueError("BRAVE_SEARCH_RESULT_COUNT must be between 1 and 20")

        database_host = (urlparse(self.DATABASE_URL).hostname or "").lower()
        if environment == "production" and database_host in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Production DATABASE_URL must not use localhost")

        if not self.DEMO_TARGET_URL:
            if environment == "production":
                raise ValueError("DEMO_TARGET_URL is required in production")
            self.DEMO_TARGET_URL = "http://127.0.0.1:8000"

        demo_url = urlparse(self.DEMO_TARGET_URL)
        if environment == "production":
            if demo_url.scheme != "https" or (demo_url.hostname or "").lower() in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError(
                    "Production DEMO_TARGET_URL must be a public HTTPS URL"
                )
            if not self.FRONTEND_ORIGINS:
                raise ValueError("FRONTEND_ORIGINS is required in production")
            backend_host = (urlparse(self.BACKEND_URL).hostname or "").lower()
            if backend_host in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError(
                    "Production BACKEND_URL must identify the deployed backend"
                )

        return self

    @property
    def frontend_origins(self) -> list[str]:
        if self.FRONTEND_ORIGINS:
            return [
                origin.strip().rstrip("/")
                for origin in self.FRONTEND_ORIGINS.split(",")
                if origin.strip()
            ]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
