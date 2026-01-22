"""公告管理和系统配置API"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..models.app_version import Announcement, SystemConfig
from ..schemas.admin import (
    AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse,
    AnnouncementListResponse, SystemConfigCreate, SystemConfigUpdate,
    SystemConfigResponse, SystemConfigListResponse
)
from ..core.deps import get_current_admin

router = APIRouter(tags=["系统管理"])


# ========== 公告管理（管理员） ==========
admin_announcement_router = APIRouter(prefix="/admin/announcements")


@admin_announcement_router.get("", response_model=AnnouncementListResponse, summary="获取公告列表")
async def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, description="公告类型"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取公告列表（管理员）"""
    query = db.query(Announcement)
    
    if type:
        query = query.filter(Announcement.type == type)
    if is_active is not None:
        query = query.filter(Announcement.is_active == is_active)
    
    total = query.count()
    items = query.order_by(Announcement.priority.desc(), Announcement.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return AnnouncementListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AnnouncementResponse.model_validate(a) for a in items]
    )


@admin_announcement_router.post("", response_model=AnnouncementResponse, summary="创建公告")
async def create_announcement(
    data: AnnouncementCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """创建公告（管理员）"""
    announcement = Announcement(
        title=data.title,
        content=data.content,
        type=data.type,
        position=data.position,
        priority=data.priority,
        start_at=data.start_at,
        end_at=data.end_at,
        is_active=True
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


@admin_announcement_router.get("/{announcement_id}", response_model=AnnouncementResponse, summary="获取公告详情")
async def get_announcement(
    announcement_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取公告详情（管理员）"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return AnnouncementResponse.model_validate(announcement)


@admin_announcement_router.put("/{announcement_id}", response_model=AnnouncementResponse, summary="更新公告")
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """更新公告（管理员）"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(announcement, field, value)
    
    db.commit()
    db.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


@admin_announcement_router.delete("/{announcement_id}", summary="删除公告")
async def delete_announcement(
    announcement_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除公告（管理员）"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    
    db.delete(announcement)
    db.commit()
    return {"message": "公告已删除"}


# ========== 系统配置（管理员） ==========
admin_config_router = APIRouter(prefix="/admin/configs")


@admin_config_router.get("", response_model=SystemConfigListResponse, summary="获取配置列表")
async def list_configs(
    group: Optional[str] = Query(None, description="配置分组"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取系统配置列表（管理员）"""
    query = db.query(SystemConfig)
    if group:
        query = query.filter(SystemConfig.config_group == group)
    
    configs = query.order_by(SystemConfig.config_group, SystemConfig.config_key).all()
    
    # 敏感配置隐藏值
    items = []
    for c in configs:
        resp = SystemConfigResponse.model_validate(c)
        if c.is_sensitive:
            resp.config_value = "******"
        items.append(resp)
    
    return SystemConfigListResponse(items=items)


@admin_config_router.post("", response_model=SystemConfigResponse, summary="创建配置")
async def create_config(
    data: SystemConfigCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """创建系统配置（管理员）"""
    if db.query(SystemConfig).filter(SystemConfig.config_key == data.config_key).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="配置键已存在")
    
    config = SystemConfig(
        config_key=data.config_key,
        config_value=data.config_value,
        config_group=data.config_group,
        description=data.description,
        is_sensitive=data.is_sensitive
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return SystemConfigResponse.model_validate(config)


@admin_config_router.put("/{config_key}", response_model=SystemConfigResponse, summary="更新配置")
async def update_config(
    config_key: str,
    data: SystemConfigUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """更新系统配置（管理员）"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    return SystemConfigResponse.model_validate(config)


@admin_config_router.delete("/{config_key}", summary="删除配置")
async def delete_config(
    config_key: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除系统配置（管理员）"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    
    db.delete(config)
    db.commit()
    return {"message": "配置已删除"}


# ========== 公开接口（APP调用） ==========
public_router = APIRouter(prefix="/public")


@public_router.get("/announcements", response_model=list[AnnouncementResponse], summary="获取有效公告")
async def get_active_announcements(
    position: Optional[str] = Query(None, description="显示位置: home/share/all"),
    db: Session = Depends(get_db)
):
    """获取当前有效的公告列表（供APP调用）"""
    now = datetime.utcnow()
    query = db.query(Announcement).filter(Announcement.is_active == True)
    
    # 位置筛选
    if position:
        query = query.filter(
            (Announcement.position == position) | (Announcement.position == "all")
        )
    
    # 时间筛选
    query = query.filter(
        (Announcement.start_at == None) | (Announcement.start_at <= now)
    ).filter(
        (Announcement.end_at == None) | (Announcement.end_at >= now)
    )
    
    announcements = query.order_by(Announcement.priority.desc(), Announcement.created_at.desc()).all()
    return [AnnouncementResponse.model_validate(a) for a in announcements]


# 合并路由
router.include_router(admin_announcement_router)
router.include_router(admin_config_router)
router.include_router(public_router)

