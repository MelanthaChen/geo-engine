from dotenv import load_dotenv

from pydantic_settings import BaseSettings

import os


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Settings(BaseSettings):

    OPENAI_API_KEY: str

    DATABASE_URL: str

    REDDIT_USERNAME: str | None = None

    REDDIT_PASSWORD: str | None = None

    PUBLISH_DRY_RUN: bool = True

    ACCOUNT_ID: int | None = None

    AGENT_NAME: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
