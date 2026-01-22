"""用户账号体系数据库模型（简化版 - 基于user_type的权限系统）"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    """用户表

    权限系统说明：
    - user_type 直接决定用户权限，不再需要Role和Permission表
    - user: 普通用户（7个基础权限）
    - vip: VIP用户（13个扩展权限）
    - admin: 管理员（所有权限）
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # 用户信息
    nickname = Column(String(100))
    avatar_url = Column(String(500))

    # 状态
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # 邮箱/手机验证

    # 用户类型: user=普通用户, vip=VIP用户, admin=管理员
    # 直接决定权限，不再需要Role表
    user_type = Column(String(20), default="user", nullable=False, index=True)

    # VIP相关
    vip_expire_at = Column(DateTime)

    # 统计
    share_count = Column(Integer, default=0)  # 分享数量
    login_count = Column(Integer, default=0)  # 登录次数
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(50))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联（简化，删除roles关联）
    shares = relationship("ShareLink", foreign_keys="[ShareLink.submitter_id]", back_populates="submitter")


# ❌ 删除 Role 类 - 不再需要
# ❌ 删除 Permission 类 - 不再需要
# ❌ 删除 user_roles 关联表 - 不再需要
# ❌ 删除 role_permissions 关联表 - 不再需要


class UserToken(Base):
    """用户Token表 - 用于刷新Token和Token黑名单"""
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_type = Column(String(20), nullable=False)  # access, refresh
    token_hash = Column(String(255), nullable=False, index=True)
    
    # 是否已撤销
    is_revoked = Column(Boolean, default=False)
    
    # 设备信息
    device_info = Column(String(255))
    ip_address = Column(String(50))
    
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # 关联
    user = relationship("User")

