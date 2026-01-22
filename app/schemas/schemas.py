from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ========== 元数据相关 ==========
class MetadataSearchRequest(BaseModel):
    title: str
    year: Optional[int] = None
    media_type: Optional[str] = "movie"  # movie, tv


class MetadataResponse(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    plot: Optional[str] = None
    rating: Optional[float] = None
    runtime: Optional[int] = None
    genres: Optional[List[str]] = None
    status: Optional[str] = None
    total_seasons: Optional[int] = None
    total_episodes: Optional[int] = None

    class Config:
        from_attributes = True


class EpisodeResponse(BaseModel):
    """剧集信息"""
    id: int
    episode_number: int
    name: Optional[str] = None
    overview: Optional[str] = None
    still_url: Optional[str] = None
    air_date: Optional[str] = None
    runtime: Optional[int] = None
    vote_average: Optional[float] = None

    class Config:
        from_attributes = True


class SeasonResponse(BaseModel):
    """季信息"""
    id: int
    season_number: int
    name: Optional[str] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    air_date: Optional[str] = None
    episode_count: Optional[int] = None
    episodes: Optional[List[EpisodeResponse]] = None

    class Config:
        from_attributes = True


# ========== 分享人相关 ==========
class SharerResponse(BaseModel):
    """分享人信息"""
    id: int
    sharer_id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    drive_type: str
    share_count: int = 0

    class Config:
        from_attributes = True


# ========== 分享链接相关 ==========
class ShareLinkCreate(BaseModel):
    drive_type: str
    share_url: str
    password: Optional[str] = None


class ShareFileResponse(BaseModel):
    id: int
    file_id: str
    file_name: str
    clean_name: Optional[str] = None
    file_size: int
    file_path: Optional[str] = None
    is_directory: bool
    file_type: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    # 电影合集时的元数据
    media_id: Optional[int] = None
    poster_url: Optional[str] = None

    class Config:
        from_attributes = True


class ShareLinkResponse(BaseModel):
    id: int
    drive_type: str
    share_url: str
    share_code: Optional[str] = None
    password: Optional[str] = None
    raw_title: Optional[str] = None
    clean_title: Optional[str] = None
    share_type: Optional[str] = None  # tv, movie, movie_collection
    media_id: Optional[int] = None
    poster_url: Optional[str] = None
    file_count: int
    view_count: int
    save_count: int
    status: str
    created_at: datetime
    # 分享人信息
    sharer: Optional[SharerResponse] = None
    # 关联的影视元数据
    media_info: Optional[MetadataResponse] = None
    # 文件列表
    files: Optional[List[ShareFileResponse]] = None

    class Config:
        from_attributes = True


class ShareListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ShareLinkResponse]
