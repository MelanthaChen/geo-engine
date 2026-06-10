from dotenv import load_dotenv

from pydantic_settings import BaseSettings

import os


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Settings(BaseSettings):

    OPENAI_API_KEY: str

    DATABASE_URL: str

    REDDIT_USERNAME: str

    REDDIT_PASSWORD: str

    PUBLISH_DRY_RUN: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
