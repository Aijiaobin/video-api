"""用户认证相关的Pydantic模型"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ========== 认证请求/响应 ==========
class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名/邮箱/手机号")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class ResetPasswordRequest(BaseModel):
    """重置密码请求（管理员）"""
    new_password: str = Field(..., min_length=6, max_length=100)


# ========== 用户信息 ==========
class UserBase(BaseModel):
    """用户基础信息"""
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    user_type: str
    is_active: bool
    is_verified: bool
    share_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetail(UserBase):
    """用户详细信息"""
    vip_expire_at: Optional[datetime] = None
    login_count: int = 0
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    updated_at: Optional[datetime] = None
    roles: List[str] = []

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户更新请求"""
    nickname: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserAdminUpdate(BaseModel):
    """管理员更新用户请求"""
    nickname: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)
    user_type: Optional[str] = Field(None, description="用户类型: user, vip, admin")
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    vip_expire_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    items: List[UserBase]


# ========== 角色权限 ==========
class RoleBase(BaseModel):
    """角色基础信息"""
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_system: bool = False

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class PermissionBase(BaseModel):
    """权限基础信息"""
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None

    class Config:
        from_attributes = True


class RoleDetail(RoleBase):
    """角色详细信息（包含权限）"""
    permissions: List[PermissionBase] = []

    class Config:
        from_attributes = True


class AssignRolesRequest(BaseModel):
    """分配角色请求"""
    role_ids: List[int]


class UserAdminCreate(BaseModel):
    """管理员创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    user_type: str = Field("user", description="用户类型: user, vip, admin")
    is_active: bool = Field(True, description="是否启用")
    role_ids: Optional[List[int]] = Field(None, description="角色ID列表")

