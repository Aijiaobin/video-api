"""用户账号体系数据库模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


# 用户-角色关联表
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """用户表"""
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
    user_type = Column(String(20), default="user")
    
    # VIP相关
    vip_expire_at = Column(DateTime)
    
    # 统计
    share_count = Column(Integer, default=0)  # 分享数量
    login_count = Column(Integer, default=0)  # 登录次数
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(50))
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    shares = relationship("ShareLink", foreign_keys="[ShareLink.submitter_id]", back_populates="submitter")


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # admin, user, vip
    display_name = Column(String(100))  # 显示名称
    description = Column(Text)
    
    # 是否系统内置角色（不可删除）
    is_system = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # share:create, share:delete, user:manage
    display_name = Column(String(100))
    description = Column(Text)
    
    # 权限分组
    group = Column(String(50))  # share, user, system
    
    created_at = Column(DateTime, server_default=func.now())

    # 关联
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


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

