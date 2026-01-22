"""APP版本管理相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== APP版本 ==========
class AppVersionCreate(BaseModel):
    """创建版本请求"""
    version_code: int = Field(..., description="版本号数字")
    version_name: str = Field(..., max_length=50, description="版本名称，如1.0.0")
    update_title: Optional[str] = Field(None, max_length=200, description="更新标题")
    update_content: Optional[str] = Field(None, description="更新说明（Markdown）")
    download_url: str = Field(..., max_length=500, description="APK下载地址")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    file_md5: Optional[str] = Field(None, max_length=32, description="文件MD5")
    is_force_update: bool = Field(False, description="是否强制更新")
    min_version_code: Optional[int] = Field(None, description="最低支持版本")


class AppVersionUpdate(BaseModel):
    """更新版本请求"""
    update_title: Optional[str] = Field(None, max_length=200)
    update_content: Optional[str] = None
    download_url: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = None
    file_md5: Optional[str] = Field(None, max_length=32)
    is_force_update: Optional[bool] = None
    min_version_code: Optional[int] = None


class AppVersionResponse(BaseModel):
    """版本响应"""
    id: int
    version_code: int
    version_name: str
    update_title: Optional[str] = None
    update_content: Optional[str] = None
    download_url: str
    file_size: Optional[int] = None
    file_md5: Optional[str] = None
    is_force_update: bool
    min_version_code: Optional[int] = None
    is_published: bool
    published_at: Optional[datetime] = None
    download_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AppVersionListResponse(BaseModel):
    """版本列表响应"""
    total: int
    page: int
    page_size: int
    items: List[AppVersionResponse]


class CheckUpdateRequest(BaseModel):
    """检查更新请求"""
    current_version_code: int = Field(..., description="当前版本号")


class CheckUpdateResponse(BaseModel):
    """检查更新响应"""
    has_update: bool = Field(..., description="是否有更新")
    is_force: bool = Field(False, description="是否强制更新")
    version: Optional[AppVersionResponse] = None


# ========== 公告 ==========
class AnnouncementCreate(BaseModel):
    """创建公告请求"""
    title: str = Field(..., max_length=200, description="公告标题")
    content: str = Field(..., description="公告内容（Markdown）")
    type: str = Field("notice", description="公告类型: notice/update/warning/event")
    position: str = Field("all", description="显示位置: home/share/all")
    priority: int = Field(0, description="优先级")
    start_at: Optional[datetime] = Field(None, description="开始时间")
    end_at: Optional[datetime] = Field(None, description="结束时间")


class AnnouncementUpdate(BaseModel):
    """更新公告请求"""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    type: Optional[str] = None
    position: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    """公告响应"""
    id: int
    title: str
    content: str
    type: str
    position: str
    priority: int
    is_active: bool
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    """公告列表响应"""
    total: int
    page: int
    page_size: int
    items: List[AnnouncementResponse]


# ========== 系统配置 ==========
class SystemConfigCreate(BaseModel):
    """创建配置请求"""
    config_key: str = Field(..., max_length=100, description="配置键")
    config_value: Optional[str] = Field(None, description="配置值")
    config_group: Optional[str] = Field(None, max_length=50, description="配置分组")
    description: Optional[str] = Field(None, max_length=255, description="配置说明")
    is_sensitive: bool = Field(False, description="是否敏感配置")


class SystemConfigUpdate(BaseModel):
    """更新配置请求"""
    config_value: Optional[str] = None
    description: Optional[str] = Field(None, max_length=255)


class SystemConfigResponse(BaseModel):
    """配置响应"""
    id: int
    config_key: str
    config_value: Optional[str] = None
    config_group: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SystemConfigListResponse(BaseModel):
    """配置列表响应"""
    items: List[SystemConfigResponse]

