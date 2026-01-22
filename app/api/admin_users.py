"""用户管理API（管理员）：用户列表、用户详情、禁用/启用、角色分配等"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..database import get_db
from ..models.user import User, Role, Permission
from ..schemas.user import (
    UserBase, UserDetail, UserAdminUpdate, UserListResponse,
    ResetPasswordRequest, RoleBase, RoleCreate, RoleDetail,
    PermissionBase, AssignRolesRequest, UserAdminCreate
)
from ..core.security import get_password_hash
from ..core.deps import get_current_admin

router = APIRouter(prefix="/admin/users", tags=["用户管理"])


# ========== 用户管理 ==========
@router.post("", response_model=UserDetail, summary="创建用户")
async def create_user(
    user_data: UserAdminCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    创建新用户（管理员）

    - 检查用户名、邮箱、手机号唯一性
    - 支持设置用户类型和角色
    - 自动哈希密码
    """
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    if user_data.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )

    # 检查手机号是否已存在
    if user_data.phone:
        if db.query(User).filter(User.phone == user_data.phone).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被注册"
            )

    # 创建用户
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        email=user_data.email,
        phone=user_data.phone,
        nickname=user_data.nickname or user_data.username,
        user_type=user_data.user_type,
        is_active=user_data.is_active,
        is_verified=True  # 管理员创建的用户默认已验证
    )

    # 分配角色
    if user_data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        new_user.roles = roles

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserDetail(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        phone=new_user.phone,
        nickname=new_user.nickname,
        avatar_url=new_user.avatar_url,
        user_type=new_user.user_type,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        share_count=new_user.share_count,
        created_at=new_user.created_at,
        vip_expire_at=new_user.vip_expire_at,
        login_count=new_user.login_count,
        last_login_at=new_user.last_login_at,
        last_login_ip=new_user.last_login_ip,
        updated_at=new_user.updated_at,
        roles=[role.name for role in new_user.roles]
    )


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/昵称/邮箱/手机号）"),
    user_type: Optional[str] = Query(None, description="用户类型筛选"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取用户列表（管理员）

    支持分页、关键词搜索、用户类型筛选、状态筛选
    """
    query = db.query(User)

    # 关键词搜索
    if keyword:
        query = query.filter(
            or_(
                User.username.ilike(f"%{keyword}%"),
                User.nickname.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
                User.phone.ilike(f"%{keyword}%")
            )
        )

    # 用户类型筛选
    if user_type:
        query = query.filter(User.user_type == user_type)

    # 状态筛选
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # 统计总数
    total = query.count()

    # 分页查询
    users = query.order_by(User.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserBase.model_validate(u) for u in users]
    )


@router.get("/{user_id}", response_model=UserDetail, summary="获取用户详情")
async def get_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取指定用户的详细信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserDetail(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        user_type=user.user_type,
        is_active=user.is_active,
        is_verified=user.is_verified,
        share_count=user.share_count,
        created_at=user.created_at,
        vip_expire_at=user.vip_expire_at,
        login_count=user.login_count,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
        updated_at=user.updated_at,
        roles=[role.name for role in user.roles]
    )


@router.put("/{user_id}", response_model=UserDetail, summary="更新用户信息")
async def update_user(
    user_id: int,
    update_data: UserAdminUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """更新指定用户的信息（管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 检查邮箱唯一性
    if update_data.email and update_data.email != user.email:
        if db.query(User).filter(User.email == update_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )

    # 检查手机号唯一性
    if update_data.phone and update_data.phone != user.phone:
        if db.query(User).filter(User.phone == update_data.phone).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被使用"
            )

    # 更新字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return UserDetail(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        user_type=user.user_type,
        is_active=user.is_active,
        is_verified=user.is_verified,
        share_count=user.share_count,
        created_at=user.created_at,
        vip_expire_at=user.vip_expire_at,
        login_count=user.login_count,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
        updated_at=user.updated_at,
        roles=[role.name for role in user.roles]
    )


@router.post("/{user_id}/disable", summary="禁用用户")
async def disable_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """禁用指定用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己"
        )

    user.is_active = False
    db.commit()

    return {"message": "用户已禁用"}


@router.post("/{user_id}/enable", summary="启用用户")
async def enable_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """启用指定用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    user.is_active = True
    db.commit()

    return {"message": "用户已启用"}




# ========== 角色管理 ==========
@router.get("/roles", response_model=List[RoleDetail], summary="获取角色列表")
async def list_roles(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取所有角色列表（包含权限）"""
    roles = db.query(Role).all()
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


@router.post("/roles", response_model=RoleDetail, summary="创建角色")
async def create_role(
    role_data: RoleCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """创建新角色（管理员）"""
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


@router.put("/roles/{role_id}", response_model=RoleDetail, summary="更新角色")
async def update_role(
    role_id: int,
    role_data: RoleCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """更新角色信息（管理员）"""
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


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除角色（管理员）"""
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

    db.delete(role)
    db.commit()

    return {"message": "角色已删除"}


# ========== 权限管理 ==========
@router.get("/permissions", response_model=List[PermissionBase], summary="获取权限列表")
async def list_permissions(
    group: Optional[str] = Query(None, description="权限分组筛选"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取所有权限列表（管理员）"""
    query = db.query(Permission)

    if group:
        query = query.filter(Permission.group == group)

    permissions = query.order_by(Permission.group, Permission.name).all()

    return [
        PermissionBase(
            id=perm.id,
            name=perm.name,
            display_name=perm.display_name,
            description=perm.description,
            group=perm.group
        ) for perm in permissions
    ]


@router.post("/roles/{role_id}/permissions", summary="分配权限给角色")
async def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """为角色分配权限（管理员）"""
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
        "permissions": [p.name for p in permissions]
    }

@router.post("/{user_id}/reset-password", summary="重置用户密码")
async def reset_user_password(
    user_id: int,
    password_data: ResetPasswordRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """重置指定用户的密码（管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    user.password_hash = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "密码已重置"}


@router.post("/{user_id}/roles", summary="分配角色")
async def assign_roles(
    user_id: int,
    roles_data: AssignRolesRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """为用户分配角色"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 获取角色
    roles = db.query(Role).filter(Role.id.in_(roles_data.role_ids)).all()
    if len(roles) != len(roles_data.role_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分角色不存在"
        )

    # 更新用户角色
    user.roles = roles
    db.commit()

    return {"message": "角色分配成功", "roles": [r.name for r in roles]}


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除指定用户（软删除，实际是禁用）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )

    # 软删除：禁用用户
    user.is_active = False
    db.commit()

    return {"message": "用户已删除"}

