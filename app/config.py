from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # SQLite 数据库配置 - 默认使用本地文件
    database_url: str = "sqlite:///./video.db"

    # TMDB API 配置 - 从数据库系统配置表读取，不再从环境变量读取
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # Redis 配置 - 可选，如果不配置则不使用缓存
    redis_url: str = ""

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
