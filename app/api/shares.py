from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.models import ShareLink, ShareFile, MediaMetadata, Sharer
from ..models.user import User
from ..schemas.schemas import (
    ShareLinkCreate, ShareLinkResponse, ShareListResponse,
    ShareFileResponse, SharerResponse, MetadataResponse
)
from ..services.share_parser import tianyi_parser, clean_share_url, extract_password_from_text
from ..services.tmdb_service import TMDBService
from ..core.deps import get_current_user, get_current_user_optional, require_permission
import json

router = APIRouter(prefix="/shares", tags=["shares"])


def get_or_create_sharer(db: Session, sharer_info: dict, drive_type: str) -> Optional[Sharer]:
    """获取或创建分享人"""
    if not sharer_info or not sharer_info.get("sharer_id"):
        return None

    sharer = db.query(Sharer).filter(
        Sharer.sharer_id == sharer_info["sharer_id"]
    ).first()

    if not sharer:
        sharer = Sharer(
            sharer_id=sharer_info["sharer_id"],
            nickname=sharer_info.get("nickname", ""),
            avatar_url=sharer_info.get("avatar_url", ""),
            drive_type=drive_type,
            share_count=1
        )
        db.add(sharer)
        db.commit()
        db.refresh(sharer)
    else:
        # 更新分享数量
        sharer.share_count += 1
        if sharer_info.get("nickname"):
            sharer.nickname = sharer_info["nickname"]
        if sharer_info.get("avatar_url"):
            sharer.avatar_url = sharer_info["avatar_url"]
        db.commit()

    return sharer


async def parse_and_update_share(share_id: int, share_url: str, password: str, drive_type: str):
    """后台任务：解析分享链接并更新数据库，然后刮削元数据"""
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
        if not share:
            return

        # 根据网盘类型选择解析器
        result = None
        if drive_type == "tianyi":
            result = await tianyi_parser.parse_share(share_url, password)

        if result:
            # 更新分享信息
            share.raw_title = result.get("raw_title", "")
            share.clean_title = result.get("clean_title", "")
            share.share_type = result.get("share_type", "tv")
            share.share_code = result.get("share_code", "")
            share.file_count = result.get("file_count", 0)

            # 处理分享人
            sharer_info = result.get("sharer_info", {})
            if sharer_info and sharer_info.get("sharer_id"):
                sharer = get_or_create_sharer(db, sharer_info, drive_type)
                if sharer:
                    share.sharer_id = sharer.id

            # 保存文件列表（重新解析时先清空旧列表，避免重复）
            db.query(ShareFile).filter(ShareFile.share_link_id == share_id).delete()

            for f in result.get("files", []):
                db_file = ShareFile(
                    share_link_id=share_id,
                    file_id=f["file_id"],
                    file_name=f["file_name"],
                    clean_name=f.get("clean_name"),
                    file_size=f["file_size"],
                    is_directory=f["is_directory"],
                    file_type=f.get("file_type", "other"),
                    season_number=f.get("season_number"),
                    episode_number=f.get("episode_number"),
                    resolution=f.get("resolution"),
                    video_codec=f.get("video_codec"),
                    audio_codec=f.get("audio_codec")
                )
                db.add(db_file)

            db.commit()

            # 保存提取的 TMDB ID
            extracted_tmdb_id = result.get("tmdb_id")
            if extracted_tmdb_id:
                share.extracted_tmdb_id = extracted_tmdb_id

            db.commit()

            # 刮削元数据
            clean_title = result.get("clean_title", "")
            share_type = result.get("share_type", "tv")

            if clean_title and share_type != "movie_collection":
                # TV 或单部电影：刮削整体
                await scrape_share_metadata_legacy(db, share, clean_title, share_type, result.get("year"))
            elif share_type == "movie_collection":
                # 电影合集：刮削每个视频文件
                await scrape_collection_files(db, share)

    except Exception as e:
        print(f"Parse share error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def scrape_share_metadata_legacy(db: Session, share: ShareLink, clean_title: str, share_type: str, year: int = None):
    """刮削分享的元数据（TV剧集或单部电影）- 旧版本，用于 parse_and_update_share"""
    try:
        # 根据分享类型确定媒体类型
        media_type = "tv" if share_type == "tv" else "movie"

        tmdb_service = TMDBService(db)
        metadata = await tmdb_service.search_and_cache(clean_title, year, media_type)

        if metadata:
            share.media_id = metadata.id
            share.poster_url = metadata.poster_url
            db.commit()
            print(f"Scraped metadata for '{clean_title}': {metadata.title}, poster: {metadata.poster_url}")
        else:
            print(f"No metadata found for '{clean_title}'")
    except Exception as e:
        print(f"Scrape metadata error: {e}")
        import traceback
        traceback.print_exc()


async def scrape_share_metadata(share_id: int):
    """
    重新刮削分享的元数据（从 share_id 调用）

    刮削优先级：
    1. 使用 manual_tmdb_id（如果设置）
    2. 使用 extracted_tmdb_id（从标题提取）
    3. 使用 manual_title 或 clean_title 搜索TMDB
    """
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
        if not share:
            print(f"Share {share_id} not found")
            return

        tmdb_service = TMDBService(db)
        metadata = None

        # 根据分享类型确定媒体类型
        media_type = "tv" if share.share_type == "tv" else "movie"

        # 优先级1: 使用 manual_tmdb_id
        if share.manual_tmdb_id:
            print(f"Using manual_tmdb_id: {share.manual_tmdb_id}")
            metadata = await tmdb_service.get_or_fetch(share.manual_tmdb_id, media_type)

        # 优先级2: 使用 extracted_tmdb_id
        elif share.extracted_tmdb_id:
            print(f"Using extracted_tmdb_id: {share.extracted_tmdb_id}")
            metadata = await tmdb_service.get_or_fetch(share.extracted_tmdb_id, media_type)

        # 优先级3: 使用标题搜索
        else:
            # 优先使用 manual_title，否则使用 clean_title
            search_title = share.manual_title or share.clean_title
            if not search_title:
                print(f"No title available for share {share_id}")
                return

            print(f"Searching TMDB with title: {search_title}")
            metadata = await tmdb_service.search_and_cache(search_title, None, media_type)

        # 更新分享的元数据
        if metadata:
            share.media_id = metadata.id
            share.poster_url = metadata.poster_url
            db.commit()
            print(f"Scraped metadata for share {share_id}: {metadata.title}, poster: {metadata.poster_url}")
        else:
            print(f"No metadata found for share {share_id}")

    except Exception as e:
        print(f"Scrape metadata error for share {share_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def scrape_collection_files(db: Session, share: ShareLink):
    """刮削电影合集中的每个视频文件"""
    try:
        tmdb_service = TMDBService(db)

        # 获取所有视频文件
        video_files = db.query(ShareFile).filter(
            ShareFile.share_link_id == share.id,
            ShareFile.file_type == "video"
        ).all()

        for file in video_files:
            # 从文件名提取电影名称
            clean_name = file.clean_name or file.file_name
            # 移除扩展名
            if '.' in clean_name:
                clean_name = clean_name.rsplit('.', 1)[0]

            # 尝试刮削
            metadata = await tmdb_service.search_and_cache(clean_name, None, "movie")
            if metadata:
                file.media_id = metadata.id
                file.poster_url = metadata.poster_url
                print(f"Scraped file '{file.file_name}': {metadata.title}")

        db.commit()
    except Exception as e:
        print(f"Scrape collection files error: {e}")
        import traceback
        traceback.print_exc()


@router.post("", response_model=ShareLinkResponse)
async def create_share(
    share: ShareLinkCreate,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user_optional),  # 允许匿名提交
    db: Session = Depends(get_db)
):
    """
    提交分享链接（允许匿名提交）

    请求体:
    - drive_type: 网盘类型 (tianyi=天翼云盘, aliyun=阿里云盘, quark=夸克网盘)
    - share_url: 分享链接URL
    - password: 提取码 (可选)

    返回字段说明:
    - id: 分享记录ID (用于后续查询详情)
    - drive_type: 网盘类型
    - share_url: 清洗后的分享链接
    - share_code: 分享码 (从URL提取)
    - password: 提取码
    - raw_title: 原始标题 (网盘返回的原始文件夹名)
    - clean_title: 清洗后标题 (用于TMDB刮削的干净名称)
    - share_type: 分享类型 (tv=剧集, movie=单部电影, movie_collection=电影合集)
    - media_id: 关联的媒体元数据ID (外键关联media_metadata表)
    - poster_url: 海报URL (从TMDB获取)
    - file_count: 文件数量
    - view_count: 浏览次数
    - save_count: 转存次数
    - status: 状态 (active=有效, invalid=失效, deleted=已删除)
    - created_at: 创建时间
    - sharer: 分享人信息 (后台解析完成后填充)
    - media_info: 影视元数据 (后台刮削完成后填充)
    - files: 文件列表 (仅详情接口返回)

    注意: 提交后会立即返回，后台异步解析分享内容和刮削元数据
    """
    # 清理URL
    cleaned_url = clean_share_url(share.share_url)

    # 如果没有提供密码，尝试从原始文本中提取
    password = share.password
    if not password:
        password = extract_password_from_text(share.share_url)

    # 检查是否已存在
    existing = db.query(ShareLink).filter(
        ShareLink.share_url == cleaned_url
    ).first()
    if existing:
        # 如果已存在，直接返回现有的
        return _to_response(existing, db)

    # 创建分享，如果用户已登录则记录提交者ID
    db_share = ShareLink(
        drive_type=share.drive_type,
        share_url=cleaned_url,
        password=password,
        submitter_id=current_user.id if current_user else None  # 匿名提交时为 None
    )
    db.add(db_share)
    db.commit()
    db.refresh(db_share)

    # 后台解析分享链接
    background_tasks.add_task(
        parse_and_update_share,
        db_share.id,
        cleaned_url,
        password,
        share.drive_type
    )

    return _to_response(db_share, db)


@router.get("", response_model=ShareListResponse)
async def list_shares(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    drive_type: Optional[str] = None,
    share_type: Optional[str] = None,
    keyword: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    浏览分享广场

    查询参数:
    - page: 页码 (从1开始)
    - page_size: 每页数量 (1-100)
    - drive_type: 网盘类型筛选 (tianyi/aliyun/quark)
    - share_type: 分享类型筛选 (tv/movie/movie_collection)
    - keyword: 关键词搜索 (搜索标题)

    权限说明:
    - 未登录用户：查看所有已审核通过的分享
    - 普通用户：只能查看自己提交的分享
    - 管理员：查看所有分享

    返回字段说明:
    - total: 总数量
    - page: 当前页码
    - page_size: 每页数量
    - items: 分享列表，每项包含:
        - id: 分享记录ID
        - drive_type: 网盘类型
        - share_url: 分享链接
        - share_code: 分享码
        - raw_title: 原始标题
        - clean_title: 清洗后标题 (APP显示用)
        - share_type: 分享类型 (tv=剧集, movie=电影, movie_collection=电影合集)
        - poster_url: 海报URL (TMDB)
        - file_count: 文件数量
        - view_count: 浏览次数
        - sharer: 分享人信息 {id, sharer_id, nickname, avatar_url, drive_type, share_count}
        - media_info: 影视元数据 {tmdb_id, media_type, title, year, poster_url, rating, genres...}
    """
    query = db.query(ShareLink)

    # 根据用户身份过滤数据
    if current_user is None:
        # 未登录用户：只能查看已审核通过的分享
        query = query.filter(ShareLink.status == "active")
    elif current_user.user_type != "admin":
        # 普通用户：只能查看自己提交的分享
        query = query.filter(ShareLink.submitter_id == current_user.id)
    else:
        # 管理员：查看所有分享（包括待审核的）
        query = query.filter(ShareLink.status == "active")

    if drive_type:
        query = query.filter(ShareLink.drive_type == drive_type)
    if share_type:
        query = query.filter(ShareLink.share_type == share_type)
    if keyword:
        # 搜索原始标题和清洗后标题
        query = query.filter(
            (ShareLink.raw_title.ilike(f"%{keyword}%")) |
            (ShareLink.clean_title.ilike(f"%{keyword}%"))
        )

    total = query.count()
    items = query.order_by(ShareLink.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return ShareListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_to_response(item, db) for item in items]
    )


@router.get("/{share_id}", response_model=ShareLinkResponse)
async def get_share(
    share_id: int,
    db: Session = Depends(get_db)
):
    """
    获取分享详情

    路径参数:
    - share_id: 分享记录ID

    返回字段说明 (包含完整文件列表):
    - id: 分享记录ID
    - drive_type: 网盘类型
    - share_url: 分享链接
    - share_code: 分享码
    - password: 提取码
    - raw_title: 原始标题
    - clean_title: 清洗后标题
    - share_type: 分享类型 (tv/movie/movie_collection)
    - media_id: 关联的媒体元数据ID
    - poster_url: 海报URL
    - file_count: 文件数量
    - view_count: 浏览次数
    - save_count: 转存次数
    - status: 状态
    - created_at: 创建时间
    - sharer: 分享人信息
        - id: 分享人记录ID
        - sharer_id: 网盘用户ID
        - nickname: 昵称
        - avatar_url: 头像URL
        - drive_type: 网盘类型
        - share_count: 分享数量
    - media_info: 影视元数据 (TMDB)
        - tmdb_id: TMDB ID
        - media_type: 媒体类型 (tv/movie)
        - title: 标题
        - original_title: 原始标题
        - year: 年份
        - poster_url: 海报URL
        - backdrop_url: 背景图URL
        - plot: 简介
        - rating: 评分
        - runtime: 时长(分钟)
        - genres: 类型列表
        - status: 状态
        - total_seasons: 总季数 (剧集)
        - total_episodes: 总集数 (剧集)
    - files: 文件列表
        - id: 文件记录ID
        - file_id: 网盘文件ID
        - file_name: 原始文件名
        - clean_name: 清洗后文件名
        - file_size: 文件大小(字节)
        - file_path: 文件路径
        - is_directory: 是否为目录
        - file_type: 文件类型 (video/subtitle/audio/image/other)
        - season_number: 季号 (剧集)
        - episode_number: 集号 (剧集)
        - resolution: 分辨率 (4K/1080p/720p等)
        - video_codec: 视频编码 (HEVC/H264/AV1等)
        - audio_codec: 音频编码 (AAC/DTS/FLAC等)
        - media_id: 关联的媒体ID (电影合集时每个文件独立关联)
        - poster_url: 海报URL (电影合集时每个文件独立海报)
    """
    share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    # 增加浏览次数
    share.view_count += 1
    db.commit()

    return _to_response(share, db, include_files=True)


@router.delete("/{share_id}")
async def delete_share(
    share_id: int,
    current_user: User = Depends(get_current_user),  # ✅ 需要登录
    db: Session = Depends(get_db)
):
    """删除分享（需要登录，只能删除自己的分享，管理员除外）"""
    share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    # ✅ 权限检查：只能删除自己的分享，管理员可以删除任何分享
    if share.submitter_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=403,
            detail="无权删除此分享（只能删除自己创建的分享）"
        )

    share.status = "deleted"
    db.commit()
    return {"message": "删除成功"}


@router.post("/{share_id}/increase-save-count")
async def increase_save_count(
    share_id: int,
    db: Session = Depends(get_db)
):
    """
    增加转存次数

    用于客户端转存成功后调用，增加该分享的转存计数
    """
    share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    share.save_count += 1
    db.commit()
    return {"message": "转存次数已更新", "save_count": share.save_count}


def _to_response(share: ShareLink, db: Session, include_files: bool = False) -> ShareLinkResponse:
    """转换为响应模型"""
    # 文件列表
    files = None
    if include_files and share.files:
        files = [
            ShareFileResponse(
                id=f.id,
                file_id=f.file_id,
                file_name=f.file_name,
                clean_name=f.clean_name,
                file_size=f.file_size,
                file_path=f.file_path,
                is_directory=f.is_directory,
                file_type=f.file_type,
                season_number=f.season_number,
                episode_number=f.episode_number,
                resolution=f.resolution,
                video_codec=f.video_codec,
                audio_codec=f.audio_codec,
                media_id=f.media_id,
                poster_url=f.poster_url
            ) for f in share.files
        ]

    # 分享人信息
    sharer = None
    if share.sharer:
        sharer = SharerResponse(
            id=share.sharer.id,
            sharer_id=share.sharer.sharer_id,
            nickname=share.sharer.nickname,
            avatar_url=share.sharer.avatar_url,
            drive_type=share.sharer.drive_type,
            share_count=share.sharer.share_count
        )

    # 影视元数据
    media_info = None
    if share.media_info:
        media = share.media_info
        genres = None
        if media.genres:
            try:
                genres = json.loads(media.genres)
            except:
                genres = []
        media_info = MetadataResponse(
            tmdb_id=media.tmdb_id,
            media_type=media.media_type,
            title=media.title,
            original_title=media.original_title,
            year=media.year,
            poster_url=media.poster_url,
            backdrop_url=media.backdrop_url,
            plot=media.plot,
            rating=media.rating,
            runtime=media.runtime,
            genres=genres,
            status=media.status,
            total_seasons=media.total_seasons,
            total_episodes=media.total_episodes
        )

    return ShareLinkResponse(
        id=share.id,
        drive_type=share.drive_type,
        share_url=share.share_url,
        share_code=share.share_code,
        password=share.password,
        raw_title=share.raw_title,
        clean_title=share.clean_title,
        share_type=share.share_type,
        media_id=share.media_id,
        poster_url=share.poster_url,
        file_count=share.file_count,
        view_count=share.view_count,
        save_count=share.save_count,
        status=share.status,
        created_at=share.created_at,
        sharer=sharer,
        media_info=media_info,
        files=files
    )
