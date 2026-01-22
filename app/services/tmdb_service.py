import httpx
from typing import Optional, List
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models.models import MediaMetadata, TvSeason, TvEpisode
from ..models.app_version import SystemConfig
import json

settings = get_settings()

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"
TMDB_STILL_BASE = "https://image.tmdb.org/t/p/w300"  # 剧照尺寸


class TMDBService:
    """TMDB 刮削服务 - 带本地缓存"""

    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.tmdb_base_url
        # 从数据库读取 TMDB API Key
        self.api_key = self._get_tmdb_api_key()

    def _get_tmdb_api_key(self) -> str:
        """从数据库系统配置表读取 TMDB API Key"""
        config = self.db.query(SystemConfig).filter(
            SystemConfig.config_key == "tmdb_api_key"
        ).first()
        return config.config_value if config else ""
    
    async def search_and_cache(
        self, 
        title: str, 
        year: Optional[int] = None,
        media_type: str = "movie"
    ) -> Optional[MediaMetadata]:
        """搜索影视并缓存结果"""
        # 1. 先查本地缓存
        cached = self._search_local(title, year, media_type)
        if cached:
            return cached
        
        # 2. 调用 TMDB API
        tmdb_result = await self._search_tmdb(title, year, media_type)
        if not tmdb_result:
            return None
        
        # 3. 获取详情
        details = await self._get_tmdb_details(tmdb_result["id"], media_type)
        if not details:
            return None
        
        # 4. 存入数据库
        metadata = self._save_to_db(details, media_type)
        return metadata
    
    def get_by_tmdb_id(self, tmdb_id: int) -> Optional[MediaMetadata]:
        """根据 TMDB ID 获取缓存"""
        return self.db.query(MediaMetadata).filter(
            MediaMetadata.tmdb_id == tmdb_id
        ).first()
    
    async def get_or_fetch(self, tmdb_id: int, media_type: str = "movie") -> Optional[MediaMetadata]:
        """获取或从 TMDB 拉取"""
        # 先查缓存
        cached = self.get_by_tmdb_id(tmdb_id)
        if cached:
            return cached
        
        # 从 TMDB 获取
        details = await self._get_tmdb_details(tmdb_id, media_type)
        if not details:
            return None
        
        return self._save_to_db(details, media_type)
    
    def _search_local(self, title: str, year: Optional[int], media_type: str) -> Optional[MediaMetadata]:
        """本地搜索"""
        query = self.db.query(MediaMetadata).filter(
            MediaMetadata.media_type == media_type,
            MediaMetadata.title.ilike(f"%{title}%")
        )
        if year:
            query = query.filter(MediaMetadata.year == year)
        return query.first()
    
    async def _search_tmdb(self, title: str, year: Optional[int], media_type: str) -> Optional[dict]:
        """调用 TMDB 搜索 API"""
        if not self.api_key:
            return None
        
        endpoint = f"{self.base_url}/search/{media_type}"
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "zh-CN"
        }
        if year:
            params["year" if media_type == "movie" else "first_air_date_year"] = year
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                results = data.get("results", [])
                return results[0] if results else None
        except Exception:
            return None
    
    async def _get_tmdb_details(self, tmdb_id: int, media_type: str) -> Optional[dict]:
        """获取 TMDB 详情"""
        if not self.api_key:
            return None
        
        endpoint = f"{self.base_url}/{media_type}/{tmdb_id}"
        params = {"api_key": self.api_key, "language": "zh-CN"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, params=params)
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception:
            return None
    
    def _save_to_db(self, details: dict, media_type: str) -> MediaMetadata:
        """保存到数据库"""
        # 检查是否已存在
        existing = self.db.query(MediaMetadata).filter(
            MediaMetadata.tmdb_id == details["id"]
        ).first()
        if existing:
            return existing
        
        # 解析数据
        if media_type == "movie":
            title = details.get("title", "")
            original_title = details.get("original_title")
            year = int(details.get("release_date", "0000")[:4]) if details.get("release_date") else None
            runtime = details.get("runtime")
        else:
            title = details.get("name", "")
            original_title = details.get("original_name")
            year = int(details.get("first_air_date", "0000")[:4]) if details.get("first_air_date") else None
            runtime = details.get("episode_run_time", [None])[0] if details.get("episode_run_time") else None
        
        genres = [g["name"] for g in details.get("genres", [])]
        
        metadata = MediaMetadata(
            tmdb_id=details["id"],
            media_type=media_type,
            title=title,
            original_title=original_title,
            year=year,
            poster_url=f"{TMDB_IMAGE_BASE}{details['poster_path']}" if details.get("poster_path") else None,
            backdrop_url=f"{TMDB_BACKDROP_BASE}{details['backdrop_path']}" if details.get("backdrop_path") else None,
            plot=details.get("overview"),
            rating=details.get("vote_average"),
            runtime=runtime,
            genres=json.dumps(genres, ensure_ascii=False),
            status=details.get("status"),
            total_seasons=details.get("number_of_seasons"),
            total_episodes=details.get("number_of_episodes")
        )
        
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(metadata)
        return metadata
    
    async def fetch_tv_seasons(self, media: MediaMetadata) -> List[TvSeason]:
        """获取电视剧的所有季信息"""
        if media.media_type != "tv":
            return []
        
        # 检查是否已有季信息
        existing_seasons = self.db.query(TvSeason).filter(
            TvSeason.media_id == media.id
        ).all()
        if existing_seasons:
            return existing_seasons
        
        # 从 TMDB 获取详情（包含季列表）
        details = await self._get_tmdb_details(media.tmdb_id, "tv")
        if not details or "seasons" not in details:
            return []
        
        seasons = []
        for s in details.get("seasons", []):
            season = TvSeason(
                media_id=media.id,
                tmdb_season_id=s.get("id"),
                season_number=s.get("season_number", 0),
                name=s.get("name"),
                overview=s.get("overview"),
                poster_url=f"{TMDB_IMAGE_BASE}{s['poster_path']}" if s.get("poster_path") else None,
                air_date=s.get("air_date"),
                episode_count=s.get("episode_count", 0)
            )
            self.db.add(season)
            seasons.append(season)
        
        self.db.commit()
        return seasons
    
    async def fetch_season_episodes(self, media: MediaMetadata, season_number: int) -> List[TvEpisode]:
        """获取某一季的所有集信息"""
        # 先找到季
        season = self.db.query(TvSeason).filter(
            TvSeason.media_id == media.id,
            TvSeason.season_number == season_number
        ).first()
        
        if not season:
            # 先获取季信息
            await self.fetch_tv_seasons(media)
            season = self.db.query(TvSeason).filter(
                TvSeason.media_id == media.id,
                TvSeason.season_number == season_number
            ).first()
            if not season:
                return []
        
        # 检查是否已有集信息
        existing_episodes = self.db.query(TvEpisode).filter(
            TvEpisode.season_id == season.id
        ).all()
        if existing_episodes:
            return existing_episodes
        
        # 从 TMDB 获取季详情
        season_details = await self._get_season_details(media.tmdb_id, season_number)
        if not season_details or "episodes" not in season_details:
            return []
        
        episodes = []
        for e in season_details.get("episodes", []):
            episode = TvEpisode(
                season_id=season.id,
                tmdb_episode_id=e.get("id"),
                episode_number=e.get("episode_number", 0),
                name=e.get("name"),
                overview=e.get("overview"),
                still_url=f"{TMDB_STILL_BASE}{e['still_path']}" if e.get("still_path") else None,
                air_date=e.get("air_date"),
                runtime=e.get("runtime"),
                vote_average=e.get("vote_average")
            )
            self.db.add(episode)
            episodes.append(episode)
        
        self.db.commit()
        return episodes
    
    async def _get_season_details(self, tmdb_id: int, season_number: int) -> Optional[dict]:
        """获取 TMDB 季详情"""
        if not self.api_key:
            return None
        
        endpoint = f"{self.base_url}/tv/{tmdb_id}/season/{season_number}"
        params = {"api_key": self.api_key, "language": "zh-CN"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, params=params)
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception:
            return None
