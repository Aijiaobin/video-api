"""APP版本管理API：版本发布、版本列表、版本检测等"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..models.app_version import AppVersion
from ..schemas.admin import (
    AppVersionCreate, AppVersionUpdate, AppVersionResponse,
    AppVersionListResponse, CheckUpdateRequest, CheckUpdateResponse
)
from ..core.deps import get_current_admin

router = APIRouter(tags=["APP版本管理"])


# ========== 管理员接口 ==========
admin_router = APIRouter(prefix="/api/admin/versions")


@admin_router.get("", response_model=AppVersionListResponse, summary="获取版本列表")
async def list_versions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取所有版本列表（管理员）"""
    query = db.query(AppVersion)
    total = query.count()
    
    versions = query.order_by(AppVersion.version_code.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return AppVersionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AppVersionResponse.model_validate(v) for v in versions]
    )


@admin_router.post("", response_model=AppVersionResponse, summary="创建新版本")
async def create_version(
    version_data: AppVersionCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """创建新版本（管理员）"""
    # 检查版本号是否已存在
    if db.query(AppVersion).filter(AppVersion.version_code == version_data.version_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="版本号已存在"
        )
    
    version = AppVersion(
        version_code=version_data.version_code,
        version_name=version_data.version_name,
        update_title=version_data.update_title,
        update_content=version_data.update_content,
        download_url=version_data.download_url,
        file_size=version_data.file_size,
        file_md5=version_data.file_md5,
        is_force_update=version_data.is_force_update,
        min_version_code=version_data.min_version_code
    )
    
    db.add(version)
    db.commit()
    db.refresh(version)
    
    return AppVersionResponse.model_validate(version)


@admin_router.get("/{version_id}", response_model=AppVersionResponse, summary="获取版本详情")
async def get_version(
    version_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取版本详情（管理员）"""
    version = db.query(AppVersion).filter(AppVersion.id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )
    return AppVersionResponse.model_validate(version)


@admin_router.put("/{version_id}", response_model=AppVersionResponse, summary="更新版本信息")
async def update_version(
    version_id: int,
    update_data: AppVersionUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """更新版本信息（管理员）"""
    version = db.query(AppVersion).filter(AppVersion.id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(version, field, value)
    
    db.commit()
    db.refresh(version)
    
    return AppVersionResponse.model_validate(version)


@admin_router.post("/{version_id}/publish", response_model=AppVersionResponse, summary="发布版本")
async def publish_version(
    version_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """发布版本（管理员）"""
    version = db.query(AppVersion).filter(AppVersion.id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )
    
    version.is_published = True
    version.published_at = datetime.utcnow()
    db.commit()
    db.refresh(version)
    
    return AppVersionResponse.model_validate(version)


@admin_router.post("/{version_id}/unpublish", response_model=AppVersionResponse, summary="取消发布")
async def unpublish_version(
    version_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """取消发布版本（管理员）"""
    version = db.query(AppVersion).filter(AppVersion.id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )
    
    version.is_published = False
    db.commit()
    db.refresh(version)
    
    return AppVersionResponse.model_validate(version)


@admin_router.delete("/{version_id}", summary="删除版本")
async def delete_version(
    version_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除版本（管理员）"""
    version = db.query(AppVersion).filter(AppVersion.id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )
    
    db.delete(version)
    db.commit()
    
    return {"message": "版本已删除"}


# ========== 公开接口（APP调用） ==========
public_router = APIRouter(prefix="/api/app")


@public_router.post("/check-update", response_model=CheckUpdateResponse, summary="检查更新")
async def check_update(
    request: CheckUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    检查APP更新（供APP调用）
    
    - **current_version_code**: 当前APP版本号
    
    返回:
    - **has_update**: 是否有更新
    - **is_force**: 是否强制更新
    - **version**: 最新版本信息
    """
    # 获取最新已发布版本
    latest = db.query(AppVersion).filter(
        AppVersion.is_published == True
    ).order_by(AppVersion.version_code.desc()).first()
    
    if not latest or latest.version_code <= request.current_version_code:
        return CheckUpdateResponse(has_update=False, is_force=False)
    
    # 判断是否强制更新
    is_force = latest.is_force_update
    if latest.min_version_code and request.current_version_code < latest.min_version_code:
        is_force = True
    
    # 增加下载计数（仅在有更新时）
    latest.download_count += 1
    db.commit()
    
    return CheckUpdateResponse(
        has_update=True,
        is_force=is_force,
        version=AppVersionResponse.model_validate(latest)
    )


@public_router.get("/latest-version", response_model=AppVersionResponse, summary="获取最新版本")
async def get_latest_version(
    db: Session = Depends(get_db)
):
    """获取最新已发布版本信息"""
    latest = db.query(AppVersion).filter(
        AppVersion.is_published == True
    ).order_by(AppVersion.version_code.desc()).first()
    
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无可用版本"
        )
    
    return AppVersionResponse.model_validate(latest)


# 合并路由
router.include_router(admin_router)
router.include_router(public_router)

