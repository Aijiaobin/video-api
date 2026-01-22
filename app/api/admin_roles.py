"""角色和权限管理API（管理员）"""
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models.user import User, Role, Permission
from ..schemas.user import (
    RoleBase, RoleCreate, RoleDetail, PermissionBase
)
from ..core.deps import get_current_admin

router = APIRouter(prefix="/admin/roles", tags=["角色权限管理"])


# ========== 权限管理（放在前面，避免路由冲突） ==========
@router.get("/permissions", response_model=List[PermissionBase], summary="获取所有权限列表")
async def list_all_permissions(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有权限列表

    - 按权限组和名称排序
    """
    permissions = db.query(Permission).order_by(Permission.group, Permission.name).all()

    return [
        PermissionBase(
            id=perm.id,
            name=perm.name,
            display_name=perm.display_name,
            description=perm.description,
            group=perm.group
        ) for perm in permissions
    ]


@router.get("/permissions/grouped", response_model=Dict[str, List[PermissionBase]], summary="获取分组权限列表")
async def list_permissions_grouped(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取按组分类的权限列表

    返回格式：
    {
        "share": [...],
        "user": [...],
        "system": [...]
    }
    """
    permissions = db.query(Permission).order_by(Permission.group, Permission.name).all()

    grouped = {}
    for perm in permissions:
        group = perm.group or "other"
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(
            PermissionBase(
                id=perm.id,
                name=perm.name,
                display_name=perm.display_name,
                description=perm.description,
                group=perm.group
            )
        )

    return grouped


# ========== 角色管理 ==========
@router.get("", response_model=List[RoleDetail], summary="获取角色列表")
async def list_roles(
    include_system: bool = Query(True, description="是否包含系统角色"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有角色列表（包含权限）

    - 支持筛选系统角色
    - 返回角色及其关联的权限列表
    """
    query = db.query(Role)

    if not include_system:
        query = query.filter(Role.is_system == False)

    roles = query.order_by(Role.is_system.desc(), Role.id).all()

    return [
        RoleDetail(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system=role.is_system,
            permissions=[
                PermissionBase(
                    id=perm.id,
                    name=perm.name,
                    display_name=perm.display_name,
                    description=perm.description,
                    group=perm.group
                ) for perm in role.permissions
            ]
        ) for role in roles
    ]


@router.get("/{role_id}", response_model=RoleDetail, summary="获取角色详情")
async def get_role(
    role_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取指定角色的详细信息"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    return RoleDetail(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        permissions=[
            PermissionBase(
                id=perm.id,
                name=perm.name,
                display_name=perm.display_name,
                description=perm.description,
                group=perm.group
            ) for perm in role.permissions
        ]
    )


@router.post("", response_model=RoleDetail, summary="创建角色")
async def create_role(
    role_data: RoleCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    创建新角色（管理员）
    
    - 检查角色名唯一性
    - 自动设置为非系统角色
    """
    # 检查角色名是否已存在
    if db.query(Role).filter(Role.name == role_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色名已存在"
        )
    
    new_role = Role(
        name=role_data.name,
        display_name=role_data.display_name,
        description=role_data.description,
        is_system=False
    )
    
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return RoleDetail(
        id=new_role.id,
        name=new_role.name,
        display_name=new_role.display_name,
        description=new_role.description,
        is_system=new_role.is_system,
        permissions=[]
    )


@router.put("/{role_id}", response_model=RoleDetail, summary="更新角色")
async def update_role(
    role_id: int,
    role_data: RoleCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    更新角色信息（管理员）
    
    - 系统角色不可修改
    - 检查角色名唯一性
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统角色不能修改"
        )

    # 检查角色名是否已被其他角色使用
    if role_data.name != role.name:
        if db.query(Role).filter(Role.name == role_data.name).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色名已存在"
            )

    role.name = role_data.name
    role.display_name = role_data.display_name
    role.description = role_data.description

    db.commit()
    db.refresh(role)

    return RoleDetail(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        permissions=[
            PermissionBase(
                id=perm.id,
                name=perm.name,
                display_name=perm.display_name,
                description=perm.description,
                group=perm.group
            ) for perm in role.permissions
        ]
    )


@router.delete("/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    删除角色（管理员）

    - 系统角色不可删除
    - 删除角色会自动解除用户关联
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统角色不能删除"
        )

    # 检查是否有用户使用该角色
    user_count = db.query(func.count(User.id)).join(User.roles).filter(Role.id == role_id).scalar()

    db.delete(role)
    db.commit()

    return {
        "message": "角色已删除",
        "affected_users": user_count
    }


# ========== 权限管理 ==========
@router.get("/permissions", response_model=List[PermissionBase], summary="获取所有权限列表")
async def list_all_permissions(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有权限列表

    - 按权限组和名称排序
    """
    permissions = db.query(Permission).order_by(Permission.group, Permission.name).all()

    return [
        PermissionBase(
            id=perm.id,
            name=perm.name,
            display_name=perm.display_name,
            description=perm.description,
            group=perm.group
        ) for perm in permissions
    ]


@router.get("/permissions/grouped", response_model=Dict[str, List[PermissionBase]], summary="获取分组权限列表")
async def list_permissions_grouped(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取按组分类的权限列表

    返回格式：
    {
        "share": [...],
        "user": [...],
        "system": [...]
    }
    """
    permissions = db.query(Permission).order_by(Permission.group, Permission.name).all()

    grouped = {}
    for perm in permissions:
        group = perm.group or "other"
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(
            PermissionBase(
                id=perm.id,
                name=perm.name,
                display_name=perm.display_name,
                description=perm.description,
                group=perm.group
            )
        )

    return grouped


@router.post("/{role_id}/permissions", summary="为角色分配权限")
async def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    为角色分配权限（管理员）

    - 系统角色不可修改权限
    - 会覆盖原有权限
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统角色不能修改权限"
        )

    # 获取权限
    permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    if len(permissions) != len(permission_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分权限不存在"
        )

    # 更新角色权限
    role.permissions = permissions
    db.commit()

    return {
        "message": "权限分配成功",
        "role": role.name,
        "permissions": [p.name for p in permissions]
    }


@router.get("/{role_id}/users", summary="获取角色关联的用户")
async def get_role_users(
    role_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取拥有指定角色的用户列表

    - 支持分页
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 查询拥有该角色的用户
    query = db.query(User).join(User.roles).filter(Role.id == role_id)

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    from ..schemas.user import UserBase

    return {
        "role": role.name,
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": [UserBase.model_validate(u) for u in users]
    }

