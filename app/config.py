from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Keep secrets out of source control; set DATABASE_URL via `.env`.
    database_url: str = "mysql+pymysql://user:password@localhost:3306/video"
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    redis_url: str = "redis://localhost:6379/0"

    # JWT配置
    jwt_secret_key: str = "video-share-platform-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24小时
    jwt_refresh_token_expire_days: int = 7  # 7天

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
