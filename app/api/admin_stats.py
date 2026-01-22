"""数据统计API：用户统计、分享统计、热门排行等"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List

from ..database import get_db
from ..models.user import User
from ..models.models import ShareLink, MediaMetadata
from ..models.app_version import AppVersion
from ..core.deps import get_current_admin

router = APIRouter(prefix="/api/admin/stats", tags=["数据统计"])


# ========== Schemas ==========
class OverviewStats(BaseModel):
    """总览统计"""
    total_users: int
    total_shares: int
    total_views: int
    total_saves: int
    today_users: int
    today_shares: int
    active_users: int
    pending_shares: int


class TrendItem(BaseModel):
    """趋势数据项"""
    date: str
    count: int


class TrendStats(BaseModel):
    """趋势统计"""
    users: List[TrendItem]
    shares: List[TrendItem]
    views: List[TrendItem]


class RankItem(BaseModel):
    """排行项"""
    id: int
    title: str
    poster_url: Optional[str] = None
    count: int
    drive_type: Optional[str] = None


class RankStats(BaseModel):
    """排行统计"""
    hot_shares: List[RankItem]  # 热门分享（浏览量）
    top_saves: List[RankItem]   # 转存排行
    top_sharers: List[dict]     # 活跃分享者


class DriveTypeStats(BaseModel):
    """网盘类型统计"""
    drive_type: str
    count: int
    percentage: float


class ShareTypeStats(BaseModel):
    """分享类型统计"""
    share_type: str
    count: int
    percentage: float


# ========== APIs ==========
@router.get("/overview", response_model=OverviewStats, summary="获取总览统计")
async def get_overview_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取系统总览统计数据"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # 用户统计
    total_users = db.query(func.count(User.id)).scalar()
    today_users = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar()
    active_users = db.query(func.count(User.id)).filter(
        User.is_active == True
    ).scalar()
    
    # 分享统计
    total_shares = db.query(func.count(ShareLink.id)).filter(
        ShareLink.status != "deleted"
    ).scalar()
    today_shares = db.query(func.count(ShareLink.id)).filter(
        ShareLink.created_at >= today_start,
        ShareLink.status != "deleted"
    ).scalar()
    pending_shares = db.query(func.count(ShareLink.id)).filter(
        ShareLink.status == "pending"
    ).scalar()
    
    # 浏览和转存统计
    total_views = db.query(func.sum(ShareLink.view_count)).scalar() or 0
    total_saves = db.query(func.sum(ShareLink.save_count)).scalar() or 0
    
    return OverviewStats(
        total_users=total_users,
        total_shares=total_shares,
        total_views=total_views,
        total_saves=total_saves,
        today_users=today_users,
        today_shares=today_shares,
        active_users=active_users,
        pending_shares=pending_shares
    )


@router.get("/trends", response_model=TrendStats, summary="获取趋势统计")
async def get_trend_stats(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取最近N天的趋势数据"""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # 生成日期列表
    date_list = []
    current = start_date
    while current <= end_date:
        date_list.append(current)
        current += timedelta(days=1)
    
    # 用户注册趋势
    user_counts = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= datetime.combine(start_date, datetime.min.time())
    ).group_by(func.date(User.created_at)).all()
    user_dict = {str(r.date): r.count for r in user_counts}
    
    # 分享提交趋势
    share_counts = db.query(
        func.date(ShareLink.created_at).label('date'),
        func.count(ShareLink.id).label('count')
    ).filter(
        ShareLink.created_at >= datetime.combine(start_date, datetime.min.time()),
        ShareLink.status != "deleted"
    ).group_by(func.date(ShareLink.created_at)).all()
    share_dict = {str(r.date): r.count for r in share_counts}
    
    # 构建趋势数据
    users_trend = [TrendItem(date=str(d), count=user_dict.get(str(d), 0)) for d in date_list]
    shares_trend = [TrendItem(date=str(d), count=share_dict.get(str(d), 0)) for d in date_list]
    
    return TrendStats(
        users=users_trend,
        shares=shares_trend,
        views=[]  # 浏览趋势需要额外的日志表支持
    )


@router.get("/rankings", response_model=RankStats, summary="获取排行统计")
async def get_ranking_stats(
    limit: int = Query(10, ge=1, le=50, description="排行数量"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取各类排行榜"""
    # 热门分享（按浏览量）
    hot_shares = db.query(ShareLink).filter(
        ShareLink.status == "active"
    ).order_by(desc(ShareLink.view_count)).limit(limit).all()
    
    hot_shares_list = [
        RankItem(
            id=s.id,
            title=s.clean_title or s.raw_title or "未知",
            poster_url=s.poster_url,
            count=s.view_count,
            drive_type=s.drive_type
        ) for s in hot_shares
    ]
    
    # 转存排行
    top_saves = db.query(ShareLink).filter(
        ShareLink.status == "active"
    ).order_by(desc(ShareLink.save_count)).limit(limit).all()
    
    top_saves_list = [
        RankItem(
            id=s.id,
            title=s.clean_title or s.raw_title or "未知",
            poster_url=s.poster_url,
            count=s.save_count,
            drive_type=s.drive_type
        ) for s in top_saves
    ]
    
    # 活跃分享者
    top_sharers = db.query(
        User.id,
        User.username,
        User.nickname,
        User.share_count
    ).filter(
        User.is_active == True
    ).order_by(desc(User.share_count)).limit(limit).all()
    
    top_sharers_list = [
        {
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "share_count": u.share_count
        } for u in top_sharers
    ]
    
    return RankStats(
        hot_shares=hot_shares_list,
        top_saves=top_saves_list,
        top_sharers=top_sharers_list
    )


@router.get("/drive-types", response_model=List[DriveTypeStats], summary="网盘类型分布")
async def get_drive_type_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取网盘类型分布统计"""
    total = db.query(func.count(ShareLink.id)).filter(
        ShareLink.status != "deleted"
    ).scalar() or 1
    
    stats = db.query(
        ShareLink.drive_type,
        func.count(ShareLink.id).label('count')
    ).filter(
        ShareLink.status != "deleted"
    ).group_by(ShareLink.drive_type).all()
    
    return [
        DriveTypeStats(
            drive_type=s.drive_type or "unknown",
            count=s.count,
            percentage=round(s.count / total * 100, 2)
        ) for s in stats
    ]


@router.get("/share-types", response_model=List[ShareTypeStats], summary="分享类型分布")
async def get_share_type_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取分享类型分布统计"""
    total = db.query(func.count(ShareLink.id)).filter(
        ShareLink.status != "deleted"
    ).scalar() or 1
    
    stats = db.query(
        ShareLink.share_type,
        func.count(ShareLink.id).label('count')
    ).filter(
        ShareLink.status != "deleted"
    ).group_by(ShareLink.share_type).all()
    
    return [
        ShareTypeStats(
            share_type=s.share_type or "unknown",
            count=s.count,
            percentage=round(s.count / total * 100, 2)
        ) for s in stats
    ]

