from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from pathlib import Path

class Settings(BaseSettings):
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DB_NAME: str = "tokyo_metro_map"

    MONGO_USER: str | None = None
    MONGO_PASSWORD: str | None = None

    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    @computed_field
    @property
    def MONGO_URL(self) -> str:
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@{self.MONGO_HOST}:{self.MONGO_PORT}"
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()