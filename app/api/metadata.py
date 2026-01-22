from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from ..database import get_db
from ..models.models import MediaMetadata, TvSeason, TvEpisode
from ..schemas.schemas import MetadataSearchRequest, MetadataResponse, SeasonResponse, EpisodeResponse
from ..services.tmdb_service import TMDBService

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.get("/search", response_model=Optional[MetadataResponse])
async def search_metadata(
    title: str = Query(..., description="影视标题"),
    year: Optional[int] = Query(None, description="年份"),
    media_type: str = Query("movie", description="类型: movie/tv"),
    db: Session = Depends(get_db)
):
    """
    搜索影视元数据
    - 先查本地缓存
    - 无则调用 TMDB 并缓存
    """
    service = TMDBService(db)
    result = await service.search_and_cache(title, year, media_type)
    
    if not result:
        return None
    
    return _to_response(result)


@router.get("/{tmdb_id}", response_model=Optional[MetadataResponse])
async def get_metadata(
    tmdb_id: int,
    media_type: str = Query("movie", description="类型: movie/tv"),
    db: Session = Depends(get_db)
):
    """
    根据 TMDB ID 获取元数据
    """
    service = TMDBService(db)
    result = await service.get_or_fetch(tmdb_id, media_type)
    
    if not result:
        return None
    
    return _to_response(result)


@router.get("/{tmdb_id}/seasons", response_model=List[SeasonResponse])
async def get_tv_seasons(
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    """
    获取电视剧的所有季信息
    """
    service = TMDBService(db)
    
    # 先获取媒体信息
    media = await service.get_or_fetch(tmdb_id, "tv")
    if not media:
        raise HTTPException(status_code=404, detail="TV show not found")
    
    seasons = await service.fetch_tv_seasons(media)
    return [_season_to_response(s) for s in seasons]


@router.get("/{tmdb_id}/seasons/{season_number}", response_model=SeasonResponse)
async def get_season_detail(
    tmdb_id: int,
    season_number: int,
    db: Session = Depends(get_db)
):
    """
    获取某一季的详细信息（包含所有集）
    """
    service = TMDBService(db)
    
    media = await service.get_or_fetch(tmdb_id, "tv")
    if not media:
        raise HTTPException(status_code=404, detail="TV show not found")
    
    # 获取季信息
    seasons = await service.fetch_tv_seasons(media)
    season = next((s for s in seasons if s.season_number == season_number), None)
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    
    # 获取集信息
    episodes = await service.fetch_season_episodes(media, season_number)
    
    return _season_to_response(season, episodes)


def _to_response(metadata: MediaMetadata) -> MetadataResponse:
    """转换为响应模型"""
    genres = []
    if metadata.genres:
        try:
            genres = json.loads(metadata.genres)
        except:
            pass
    
    return MetadataResponse(
        tmdb_id=metadata.tmdb_id,
        media_type=metadata.media_type,
        title=metadata.title,
        original_title=metadata.original_title,
        year=metadata.year,
        poster_url=metadata.poster_url,
        backdrop_url=metadata.backdrop_url,
        plot=metadata.plot,
        rating=metadata.rating,
        runtime=metadata.runtime,
        genres=genres,
        status=metadata.status,
        total_seasons=metadata.total_seasons,
        total_episodes=metadata.total_episodes
    )


def _season_to_response(season: TvSeason, episodes: List[TvEpisode] = None) -> SeasonResponse:
    """转换季为响应模型"""
    episode_responses = None
    if episodes:
        episode_responses = [_episode_to_response(e) for e in episodes]
    
    return SeasonResponse(
        id=season.id,
        season_number=season.season_number,
        name=season.name,
        overview=season.overview,
        poster_url=season.poster_url,
        air_date=season.air_date,
        episode_count=season.episode_count,
        episodes=episode_responses
    )


def _episode_to_response(episode: TvEpisode) -> EpisodeResponse:
    """转换集为响应模型"""
    return EpisodeResponse(
        id=episode.id,
        episode_number=episode.episode_number,
        name=episode.name,
        overview=episode.overview,
        still_url=episode.still_url,
        air_date=episode.air_date,
        runtime=episode.runtime,
        vote_average=episode.vote_average
    )
