from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import engine, Base
from .api import metadata, shares
from .api import auth, admin_users, admin_versions, admin_system, admin_shares, admin_stats

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Video Share API",
    description="影视分享广场 & 元数据刮削服务 & 后台管理系统",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 - 原有API（添加 /api 前缀）
app.include_router(metadata.router, prefix="/api")
app.include_router(shares.router, prefix="/api")

# 注册路由 - 认证API
app.include_router(auth.router, prefix="/api")

# 注册路由 - 管理后台API
app.include_router(admin_users.router, prefix="/api")
app.include_router(admin_versions.router, prefix="/api")
app.include_router(admin_system.router, prefix="/api")
app.include_router(admin_shares.router, prefix="/api")
app.include_router(admin_stats.router, prefix="/api")


@app.get("/api")
async def root():
    return {"message": "Video Share API", "version": "2.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# 挂载前端静态文件
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "admin-frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """服务前端页面，所有非 API 路由都返回 index.html"""
        # 如果是 API 路由，跳过
        if full_path.startswith("api/"):
            return {"error": "Not found"}

        # 检查是否是静态文件
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # 否则返回 index.html（用于 Vue Router）
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

        return {"error": "Frontend not built"}
