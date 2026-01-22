"""APP版本管理数据库模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base


class AppVersion(Base):
    """APP版本表"""
    __tablename__ = "app_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 版本信息
    version_code = Column(Integer, nullable=False, unique=True)  # 版本号数字，用于比较
    version_name = Column(String(50), nullable=False)  # 版本名称，如 "1.0.0"
    
    # 更新内容
    update_title = Column(String(200))  # 更新标题
    update_content = Column(Text)  # 更新说明（支持Markdown）
    
    # 下载信息
    download_url = Column(String(500), nullable=False)  # APK下载地址
    file_size = Column(Integer)  # 文件大小（字节）
    file_md5 = Column(String(32))  # 文件MD5校验
    
    # 更新策略
    is_force_update = Column(Boolean, default=False)  # 是否强制更新
    min_version_code = Column(Integer)  # 最低支持版本（低于此版本必须更新）
    
    # 发布状态
    is_published = Column(Boolean, default=False)  # 是否已发布
    published_at = Column(DateTime)  # 发布时间
    
    # 统计
    download_count = Column(Integer, default=0)  # 下载次数
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Announcement(Base):
    """公告表"""
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 公告内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # 支持Markdown
    
    # 公告类型: notice=通知, update=更新, warning=警告, event=活动
    type = Column(String(20), default="notice")
    
    # 显示位置: home=首页, share=分享广场, all=全部
    position = Column(String(20), default="all")
    
    # 优先级（数字越大越靠前）
    priority = Column(Integer, default=0)
    
    # 状态
    is_active = Column(Boolean, default=True)
    
    # 有效期
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 配置键值
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text)
    
    # 配置分组: tmdb, cloud_drive, system, etc.
    config_group = Column(String(50))
    
    # 配置说明
    description = Column(String(255))
    
    # 是否敏感配置（如API Key）
    is_sensitive = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

