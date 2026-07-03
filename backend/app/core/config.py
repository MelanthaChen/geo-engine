from dotenv import load_dotenv

from pydantic_settings import BaseSettings

import os


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Settings(BaseSettings):

    OPENAI_API_KEY: str

    DATABASE_URL: str

    GITHUB_TOKEN: str | None = None

    GOOGLE_SEARCH_API_KEY: str | None = None

    GOOGLE_SEARCH_ENGINE_ID: str | None = None

    REDDIT_USERNAME: str | None = None

    REDDIT_PASSWORD: str | None = None

    PUBLISH_DRY_RUN: bool = True

    ACCOUNT_ID: int | None = None

    AGENT_NAME: str | None = None

    XIAOHONGSHU_RETRIEVAL_COMMAND: str | None = None

    XIAOHONGSHU_RETRIEVAL_TIMEOUT_SECONDS: int = 180

    XIAOHONGSHU_RETRIEVAL_LIMIT: int = 20

    class Config:
        env_file = ".env"


settings = Settings()
