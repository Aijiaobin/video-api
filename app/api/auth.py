"""用户认证API：注册、登录、Token刷新、密码修改等"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.user import User, Role, UserToken
from ..schemas.user import (
    UserRegister, UserLogin, TokenResponse, RefreshTokenRequest,
    ChangePasswordRequest, UserBase, UserDetail, UserUpdate
)
from ..core.security import (
    get_password_hash, verify_password, create_tokens,
    verify_token, create_access_token
)
from ..core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserBase, summary="用户注册")
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名（3-50字符，唯一）
    - **password**: 密码（6-100字符）
    - **email**: 邮箱（可选，唯一）
    - **phone**: 手机号（可选，唯一）
    - **nickname**: 昵称（可选）
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
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        email=user_data.email,
        phone=user_data.phone,
        nickname=user_data.nickname or user_data.username,
        user_type="user",
        is_active=True
    )
    
    # 分配默认角色
    default_role = db.query(Role).filter(Role.name == "user").first()
    if default_role:
        user.roles.append(default_role)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 用户名/邮箱/手机号
    - **password**: 密码
    
    返回访问Token和刷新Token
    """
    # 查找用户（支持用户名、邮箱、手机号登录）
    user = db.query(User).filter(
        or_(
            User.username == login_data.username,
            User.email == login_data.username,
            User.phone == login_data.username
        )
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 更新登录信息
    user.login_count += 1
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    db.commit()
    
    # 生成Token
    tokens = create_tokens(user.id, user.username, user.user_type)
    
    return tokens


@router.post("/refresh", response_model=TokenResponse, summary="刷新Token")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    使用刷新Token获取新的访问Token
    
    - **refresh_token**: 刷新Token
    """
    token_data = verify_token(refresh_data.refresh_token, "refresh")
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新Token"
        )
    
    # 验证用户是否存在且有效
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    # 生成新Token
    tokens = create_tokens(user.id, user.username, user.user_type)
    
    return tokens


@router.get("/me", response_model=UserDetail, summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户的详细信息"""
    return UserDetail(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        share_count=current_user.share_count,
        created_at=current_user.created_at,
        vip_expire_at=current_user.vip_expire_at,
        login_count=current_user.login_count,
        last_login_at=current_user.last_login_at,
        last_login_ip=current_user.last_login_ip,
        updated_at=current_user.updated_at,
        roles=[role.name for role in current_user.roles]
    )


@router.put("/me", response_model=UserBase, summary="更新当前用户信息")
async def update_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前登录用户的信息"""
    # 检查邮箱唯一性
    if update_data.email and update_data.email != current_user.email:
        if db.query(User).filter(User.email == update_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
    
    # 检查手机号唯一性
    if update_data.phone and update_data.phone != current_user.phone:
        if db.query(User).filter(User.phone == update_data.phone).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被使用"
            )
    
    # 更新字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改当前用户密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码（6-100字符）
    """
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}


@router.post("/logout", summary="退出登录")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """退出登录（客户端应删除本地Token）"""
    return {"message": "退出成功"}

