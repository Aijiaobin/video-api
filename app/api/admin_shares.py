"""分享管理增强API：批量导入、审核功能、用户分享管理"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.user import User
from ..models.models import ShareLink
from ..schemas.schemas import ShareLinkResponse, ShareListResponse
from ..core.deps import get_current_user, get_current_admin, get_current_user_optional
from ..services.share_parser import clean_share_url, extract_password_from_text

router = APIRouter(tags=["分享管理"])


# ========== Schemas ==========
class BatchShareItem(BaseModel):
    """批量导入单个分享"""
    drive_type: str = Field(..., description="网盘类型: tianyi/aliyun/quark")
    share_url: str = Field(..., description="分享链接")
    password: Optional[str] = Field(None, description="提取码")


class BatchImportRequest(BaseModel):
    """批量导入请求"""
    shares: List[BatchShareItem] = Field(..., min_length=1, max_length=100)


class BatchImportResponse(BaseModel):
    """批量导入响应"""
    total: int
    success: int
    failed: int
    duplicates: int
    results: List[dict]


class ShareAuditRequest(BaseModel):
    """审核请求"""
    status: str = Field(..., description="审核状态: approved/rejected")
    reason: Optional[str] = Field(None, description="拒绝原因")


class ShareAdminListResponse(BaseModel):
    """管理员分享列表响应"""
    total: int
    page: int
    page_size: int
    items: List[dict]


# ========== 用户分享管理 ==========
user_router = APIRouter(prefix="/user/shares")


@user_router.get("", summary="获取我的分享列表")
async def get_my_shares(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户提交的分享列表"""
    query = db.query(ShareLink).filter(ShareLink.submitter_id == current_user.id)
    
    if status:
        query = query.filter(ShareLink.status == status)
    
    total = query.count()
    shares = query.order_by(ShareLink.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_share_to_dict(s) for s in shares]
    }


@user_router.post("/batch", response_model=BatchImportResponse, summary="批量提交分享")
async def batch_import_shares(
    request: BatchImportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量提交分享链接（用户）
    
    - 最多一次提交100个链接
    - 自动去重
    - 后台异步解析
    """
    results = []
    success = 0
    failed = 0
    duplicates = 0
    
    for item in request.shares:
        try:
            cleaned_url = clean_share_url(item.share_url)

            # 如果没有提供密码，尝试从原始文本中提取
            password = item.password
            if not password:
                password = extract_password_from_text(item.share_url)

            # 检查是否已存在
            existing = db.query(ShareLink).filter(ShareLink.share_url == cleaned_url).first()
            if existing:
                duplicates += 1
                results.append({
                    "share_url": item.share_url,
                    "status": "duplicate",
                    "message": "链接已存在",
                    "share_id": existing.id
                })
                continue

            # 创建分享记录
            share = ShareLink(
                drive_type=item.drive_type,
                share_url=cleaned_url,
                password=password,
                submitter_id=current_user.id,
                status="pending"  # 待审核
            )
            db.add(share)
            db.flush()

            # 添加后台解析任务
            from .shares import parse_and_update_share
            background_tasks.add_task(
                parse_and_update_share,
                share.id,
                cleaned_url,
                password,
                item.drive_type
            )
            
            success += 1
            results.append({
                "share_url": item.share_url,
                "status": "success",
                "message": "提交成功，等待审核",
                "share_id": share.id
            })
            
        except Exception as e:
            failed += 1
            results.append({
                "share_url": item.share_url,
                "status": "failed",
                "message": str(e)
            })
    
    db.commit()
    
    # 更新用户分享计数
    current_user.share_count += success
    db.commit()
    
    return BatchImportResponse(
        total=len(request.shares),
        success=success,
        failed=failed,
        duplicates=duplicates,
        results=results
    )


@user_router.delete("/{share_id}", summary="删除我的分享")
async def delete_my_share(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除自己提交的分享"""
    share = db.query(ShareLink).filter(
        ShareLink.id == share_id,
        ShareLink.submitter_id == current_user.id
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在或无权限")
    
    share.status = "deleted"
    current_user.share_count = max(0, current_user.share_count - 1)
    db.commit()
    
    return {"message": "删除成功"}


# ========== 管理员分享管理 ==========
admin_router = APIRouter(prefix="/api/admin/shares")


@admin_router.get("", summary="获取分享列表（管理员）")
async def admin_list_shares(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="状态: active/pending/rejected/deleted"),
    drive_type: Optional[str] = Query(None, description="网盘类型"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    submitter_id: Optional[int] = Query(None, description="提交者ID"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取所有分享列表（管理员）"""
    query = db.query(ShareLink)
    
    if status:
        query = query.filter(ShareLink.status == status)
    if drive_type:
        query = query.filter(ShareLink.drive_type == drive_type)
    if keyword:
        query = query.filter(
            (ShareLink.raw_title.ilike(f"%{keyword}%")) |
            (ShareLink.clean_title.ilike(f"%{keyword}%"))
        )
    if submitter_id:
        query = query.filter(ShareLink.submitter_id == submitter_id)
    
    total = query.count()
    shares = query.order_by(ShareLink.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_share_to_dict(s, include_submitter=True) for s in shares]
    }


@admin_router.post("/{share_id}/audit", summary="审核分享")
async def audit_share(
    share_id: int,
    audit: ShareAuditRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """审核分享（管理员）"""
    share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")
    
    if audit.status == "approved":
        share.status = "active"
    elif audit.status == "rejected":
        share.status = "rejected"
        share.reject_reason = audit.reason
    else:
        raise HTTPException(status_code=400, detail="无效的审核状态")
    
    share.audited_at = datetime.utcnow()
    share.audited_by = current_admin.id
    db.commit()
    
    return {"message": "审核完成", "status": share.status}


@admin_router.post("/batch-audit", summary="批量审核")
async def batch_audit_shares(
    share_ids: List[int],
    status: str = Query(..., description="审核状态: approved/rejected"),
    reason: Optional[str] = Query(None, description="拒绝原因"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """批量审核分享（管理员）"""
    shares = db.query(ShareLink).filter(ShareLink.id.in_(share_ids)).all()
    
    new_status = "active" if status == "approved" else "rejected"
    for share in shares:
        share.status = new_status
        if status == "rejected":
            share.reject_reason = reason
        share.audited_at = datetime.utcnow()
        share.audited_by = current_admin.id
    
    db.commit()
    
    return {"message": f"已审核 {len(shares)} 个分享", "status": new_status}


@admin_router.delete("/{share_id}", summary="删除分享（管理员）")
async def admin_delete_share(
    share_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除分享（管理员）"""
    share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    share.status = "deleted"
    db.commit()

    return {"message": "删除成功"}


@admin_router.post("/{share_id}/reparse", summary="重新解析分享")
async def reparse_share(
    share_id: int,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """重新解析单个分享链接，更新标题和元数据"""
    share = db.query(ShareLink).filter(ShareLink.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    from .shares import parse_and_update_share
    background_tasks.add_task(
        parse_and_update_share,
        share.id,
        share.share_url,
        share.password,
        share.drive_type
    )

    return {"message": "已提交重新解析任务", "share_id": share_id}


@admin_router.post("/reparse-all", summary="重新解析所有分享")
async def reparse_all_shares(
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """重新解析所有分享链接，更新标题和元数据"""
    shares = db.query(ShareLink).filter(ShareLink.status != "deleted").all()

    from .shares import parse_and_update_share
    for share in shares:
        background_tasks.add_task(
            parse_and_update_share,
            share.id,
            share.share_url,
            share.password,
            share.drive_type
        )

    return {"message": f"已提交 {len(shares)} 个分享的重新解析任务"}


@admin_router.post("/reparse-unparsed", summary="解析未解析的分享")
async def reparse_unparsed_shares(
    background_tasks: BackgroundTasks,
    threads: int = Query(5, ge=1, le=10, description="并发线程数"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    解析未解析的分享链接（没有元数据的）

    - 支持多线程并发解析
    - 默认5线程
    """
    # 获取未解析的分享（没有 media_id 或没有 clean_title）
    shares = db.query(ShareLink).filter(
        ShareLink.status != "deleted",
        (ShareLink.media_id == None) | (ShareLink.clean_title == None) | (ShareLink.clean_title == "")
    ).all()

    if not shares:
        return {"message": "没有需要解析的分享", "total": 0}

    # 启动后台多线程解析任务
    background_tasks.add_task(
        _batch_parse_shares_concurrent,
        [(s.id, s.share_url, s.password, s.drive_type) for s in shares],
        threads
    )

    return {"message": f"已提交 {len(shares)} 个分享的解析任务（{threads}线程）", "total": len(shares)}


async def _batch_parse_shares_concurrent(shares_data: list, max_workers: int = 5):
    """多线程并发解析分享"""
    import asyncio
    from .shares import parse_and_update_share

    semaphore = asyncio.Semaphore(max_workers)

    async def parse_with_semaphore(share_id, share_url, password, drive_type):
        async with semaphore:
            try:
                await parse_and_update_share(share_id, share_url, password, drive_type)
                print(f"[OK] Parsed share {share_id}")
            except Exception as e:
                print(f"[FAIL] Parse share {share_id} error: {e}")
            # 小延迟避免请求过快
            await asyncio.sleep(0.2)

    # 创建所有任务
    tasks = [
        parse_with_semaphore(share_id, share_url, password, drive_type)
        for share_id, share_url, password, drive_type in shares_data
    ]

    # 并发执行
    await asyncio.gather(*tasks)
    print(f"[DONE] Batch parse completed: {len(shares_data)} shares")


def _share_to_dict(share: ShareLink, include_submitter: bool = False) -> dict:
    """转换分享为字典"""
    result = {
        "id": share.id,
        "drive_type": share.drive_type,
        "share_url": share.share_url,
        "share_code": share.share_code,
        "password": share.password,
        "raw_title": share.raw_title,
        "clean_title": share.clean_title,
        "share_type": share.share_type,
        "poster_url": share.poster_url,
        "file_count": share.file_count,
        "view_count": share.view_count,
        "save_count": share.save_count,
        "status": share.status,
        "created_at": share.created_at.isoformat() if share.created_at else None
    }
    
    if include_submitter and share.submitter:
        result["submitter"] = {
            "id": share.submitter.id,
            "username": share.submitter.username,
            "nickname": share.submitter.nickname
        }
    
    return result


# 合并路由
router.include_router(user_router)
router.include_router(admin_router)

