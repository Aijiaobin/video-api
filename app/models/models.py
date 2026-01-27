from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class MediaMetadata(Base):
    """影视元数据缓存表 - 从 TMDB 刮削的数据"""
    __tablename__ = "media_metadata"
    # TMDB 的 movie 和 tv 是两套独立的 ID 系统，同一个 tmdb_id 可能对应不同的 media_type
    __table_args__ = (
        UniqueConstraint('tmdb_id', 'media_type', name='uq_tmdb_id_media_type'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id = Column(Integer, index=True, nullable=False)  # 移除 unique=True
    media_type = Column(String(20), nullable=False)  # movie, tv
    title = Column(String(255), nullable=False)
    original_title = Column(String(255))
    year = Column(Integer, index=True)
    poster_url = Column(String(500))
    backdrop_url = Column(String(500))
    plot = Column(Text)
    rating = Column(Float)
    runtime = Column(Integer)
    genres = Column(Text)  # JSON array
    status = Column(String(50))
    total_seasons = Column(Integer)
    total_episodes = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联季信息
    seasons = relationship("TvSeason", back_populates="media", cascade="all, delete-orphan")


class Sharer(Base):
    """分享人表 - 存储网盘分享者信息"""
    __tablename__ = "sharers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sharer_id = Column(String(100), unique=True, index=True, nullable=False)  # 网盘用户ID
    nickname = Column(String(255))  # 分享人昵称
    avatar_url = Column(String(500))  # 头像URL
    drive_type = Column(String(50), nullable=False)  # tianyi, aliyun, quark
    share_count = Column(Integer, default=0)  # 分享数量统计
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联分享链接
    shares = relationship("ShareLink", back_populates="sharer")


class TvSeason(Base):
    """电视剧季信息表"""
    __tablename__ = "tv_seasons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey("media_metadata.id", ondelete="CASCADE"), nullable=False)
    tmdb_season_id = Column(Integer, index=True)
    season_number = Column(Integer, nullable=False)
    name = Column(String(255))
    overview = Column(Text)
    poster_url = Column(String(500))
    air_date = Column(String(20))
    episode_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    media = relationship("MediaMetadata", back_populates="seasons")
    episodes = relationship("TvEpisode", back_populates="season", cascade="all, delete-orphan")


class TvEpisode(Base):
    """电视剧集信息表"""
    __tablename__ = "tv_episodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    season_id = Column(Integer, ForeignKey("tv_seasons.id", ondelete="CASCADE"), nullable=False)
    tmdb_episode_id = Column(Integer, index=True)
    episode_number = Column(Integer, nullable=False)
    name = Column(String(255))
    overview = Column(Text)
    still_url = Column(String(500))  # 剧照
    air_date = Column(String(20))
    runtime = Column(Integer)  # 时长（分钟）
    vote_average = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    
    season = relationship("TvSeason", back_populates="episodes")


class ShareLink(Base):
    """分享链接表"""
    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drive_type = Column(String(50), nullable=False)  # tianyi, aliyun, quark
    share_url = Column(String(500), unique=True, nullable=False)
    share_code = Column(String(100), index=True)  # 提取的分享码
    password = Column(String(50))

    # 标题相关
    raw_title = Column(String(500))  # 原始标题（网盘文件夹名）
    clean_title = Column(String(255))  # 清洗后标题（用于刮削）
    manual_title = Column(String(255))  # 手动修正的标题（优先级高于clean_title）
    manual_tmdb_id = Column(Integer)  # 手动指定的TMDB ID（优先级高于自动提取）
    extracted_tmdb_id = Column(Integer)  # 从标题中提取的TMDB ID

    # 分享类型: tv(剧集), movie(单部电影), movie_collection(电影合集)
    share_type = Column(String(50), default="tv")

    # 关联影视元数据（TV剧集或单部电影时使用）
    media_id = Column(Integer, ForeignKey("media_metadata.id"))
    poster_url = Column(String(500))

    # 分享人（网盘分享者）
    sharer_id = Column(Integer, ForeignKey("sharers.id"))

    # 提交用户（平台用户）
    submitter_id = Column(Integer, ForeignKey("users.id"))

    # 统计
    file_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)

    # 状态: active(已通过), pending(待审核), rejected(已拒绝), expired(已失效), deleted(已删除)
    status = Column(String(20), default="active")
    reject_reason = Column(String(500))  # 拒绝原因

    # 审核信息
    audited_at = Column(DateTime)  # 审核时间
    audited_by = Column(Integer, ForeignKey("users.id"))  # 审核人

    last_check_at = Column(DateTime)  # 最后有效性检测时间

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    media_info = relationship("MediaMetadata", backref="shares")
    sharer = relationship("Sharer", back_populates="shares")
    files = relationship("ShareFile", back_populates="share_link", cascade="all, delete-orphan")
    submitter = relationship("User", foreign_keys=[submitter_id], back_populates="shares")
    auditor = relationship("User", foreign_keys=[audited_by])


class ShareFile(Base):
    """分享文件表"""
    __tablename__ = "share_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    share_link_id = Column(Integer, ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String(200), nullable=False)
    file_name = Column(String(500), nullable=False)
    clean_name = Column(String(500))  # 清洗后文件名
    file_size = Column(BigInteger, default=0)
    file_path = Column(String(1000))
    is_directory = Column(Boolean, default=False)
    parent_id = Column(String(200))

    # 文件类型: video, subtitle, audio, image, other
    file_type = Column(String(50), default="other")

    # 视频文件的剧集信息（从文件名解析）
    season_number = Column(Integer)  # 季号
    episode_number = Column(Integer)  # 集号

    # 电影合集时，每个文件单独关联影视元数据
    media_id = Column(Integer, ForeignKey("media_metadata.id"))
    poster_url = Column(String(500))

    # 资源质量信息
    resolution = Column(String(20))  # 4K, 1080P, 720P
    video_codec = Column(String(20))  # HEVC, AVC, AV1
    audio_codec = Column(String(20))  # DTS, AAC, FLAC

    created_at = Column(DateTime, server_default=func.now())

    # 关联
    share_link = relationship("ShareLink", back_populates="files")
    media_info = relationship("MediaMetadata")
