"""安全相关工具：密码哈希、JWT Token生成与验证"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import hashlib

from ..config import get_settings

settings = get_settings()

# 密码哈希上下文 - 使用sha256_crypt替代bcrypt避免版本兼容问题
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: int
    username: str
    user_type: str
    token_type: str = "access"  # access or refresh


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建刷新Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_tokens(user_id: int, username: str, user_type: str) -> TokenResponse:
    """创建访问Token和刷新Token"""
    token_data = {
        "sub": str(user_id),
        "username": username,
        "user_type": user_type
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


def decode_token(token: str) -> Optional[TokenData]:
    """解码Token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        user_type: str = payload.get("user_type")
        token_type: str = payload.get("type", "access")
        
        if user_id is None or username is None:
            return None
            
        return TokenData(
            user_id=int(user_id),
            username=username,
            user_type=user_type or "user",
            token_type=token_type
        )
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """验证Token"""
    token_data = decode_token(token)
    if token_data is None:
        return None
    if token_data.token_type != token_type:
        return None
    return token_data

