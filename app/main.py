from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .api import metadata, shares
from .api import auth, admin_users, admin_versions, admin_system, admin_shares, admin_stats

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Video Share API",
    description="影视分享广场 & 元数据刮削服务 & 后台管理系统",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 - 原有API
app.include_router(metadata.router)
app.include_router(shares.router)

# 注册路由 - 认证API
app.include_router(auth.router)

# 注册路由 - 管理后台API
app.include_router(admin_users.router)
app.include_router(admin_versions.router)
app.include_router(admin_system.router)
app.include_router(admin_shares.router)
app.include_router(admin_stats.router)


@app.get("/")
async def root():
    return {"message": "Video Share API", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
