"""FastAPI依赖项：认证、权限检查等"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from .security import verify_token
from .permissions import has_permission

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    token_data = verify_token(token, "access")

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """获取当前登录用户（可选，未登录返回None）"""
    if credentials is None:
        return None

    token = credentials.credentials
    token_data = verify_token(token, "access")

    if token_data is None:
        return None

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None or not user.is_active:
        return None

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员用户"""
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


async def get_current_vip(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前VIP或管理员用户"""
    if current_user.user_type not in ["vip", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要VIP或管理员权限",
        )
    return current_user


def require_permission(permission_name: str):
    """权限检查装饰器工厂（基于user_type）

    使用示例:
        @router.delete("/{share_id}")
        async def delete_share(
            share_id: int,
            current_user: User = Depends(require_permission("share:delete")),
            db: Session = Depends(get_db)
        ):
            pass
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not has_permission(current_user.user_type, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {permission_name}",
            )
        return current_user

    return permission_checker

