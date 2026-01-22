# Video API - GitHub 部署和容器化指南

## 📋 项目概述

这是一个基于 FastAPI 的影视分享广场和元数据刮削服务，包含：
- **后端 API**：FastAPI + MySQL + Redis
- **管理后台**：Vue 3 + Element Plus
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions 自动构建和推送镜像

---

## 🚀 快速开始

### 1. 初始化 Git 仓库（如果未初始化）

```bash
cd video-api
git init
git add .
git commit -m "Initial commit: Video API with Docker support"
```

### 2. 创建 GitHub 仓库并推送

```bash
# 在 GitHub 上创建新仓库（例如：your-username/video-api）
# 然后执行以下命令：

git remote add origin https://github.com/your-username/video-api.git
git branch -M main
git push -u origin main
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入真实配置
# - DATABASE_URL: MySQL 连接字符串
# - TMDB_API_KEY: TMDB API 密钥
# - JWT_SECRET_KEY: JWT 密钥（生产环境必须修改）
```

---

## 🐳 Docker 部署

### 本地开发环境

```bash
# 启动所有服务（MySQL + Redis + API）
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 仅构建 Docker 镜像

```bash
# 构建镜像
docker build -t video-api:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="mysql+pymysql://user:pass@host:3306/video" \
  -e REDIS_URL="redis://host:6379/0" \
  -e TMDB_API_KEY="your_key" \
  --name video-api \
  video-api:latest
```

---

## 📦 GitHub Container Registry 部署

### 自动构建（推荐）

GitHub Actions 会在以下情况自动构建和推送镜像：
- 推送到 `main`/`master`/`develop` 分支
- 创建 `v*.*.*` 格式的标签
- 手动触发工作流

**镜像标签规则**：
- `ghcr.io/your-username/video-api:latest` - 最新主分支
- `ghcr.io/your-username/video-api:main` - main 分支
- `ghcr.io/your-username/video-api:v1.0.0` - 版本标签
- `ghcr.io/your-username/video-api:main-sha-abc123` - 提交 SHA

### 手动推送镜像

```bash
# 1. 登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u your-username --password-stdin

# 2. 构建镜像
docker build -t ghcr.io/your-username/video-api:latest .

# 3. 推送镜像
docker push ghcr.io/your-username/video-api:latest
```

### 拉取和运行镜像

```bash
# 拉取镜像（公开仓库）
docker pull ghcr.io/your-username/video-api:latest

# 拉取镜像（私有仓库）
echo $GITHUB_TOKEN | docker login ghcr.io -u your-username --password-stdin
docker pull ghcr.io/your-username/video-api:latest

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="mysql+pymysql://user:pass@host:3306/video" \
  -e REDIS_URL="redis://host:6379/0" \
  -e TMDB_API_KEY="your_key" \
  -e JWT_SECRET_KEY="your-secret-key" \
  --name video-api \
  ghcr.io/your-username/video-api:latest
```

---

## ⚙️ GitHub 配置

### 1. 启用 GitHub Actions

- 进入仓库 Settings → Actions → General
- 确保 "Allow all actions and reusable workflows" 已启用

### 2. 配置 Packages 权限

- 进入仓库 Settings → Actions → General
- 在 "Workflow permissions" 部分选择 "Read and write permissions"
- 勾选 "Allow GitHub Actions to create and approve pull requests"

### 3. 设置镜像可见性

构建完成后：
- 进入仓库 Packages 页面
- 点击镜像包
- Settings → Change visibility（设置为 Public 或 Private）

### 4. 配置 Secrets（可选）

如果需要额外的环境变量：
- 进入仓库 Settings → Secrets and variables → Actions
- 添加 Repository secrets：
  - `TMDB_API_KEY`
  - `JWT_SECRET_KEY`
  - 其他敏感配置

---

## 🏗️ 项目结构

```
video-api/
├── .github/
│   └── workflows/
│       └── docker-publish.yml    # GitHub Actions 工作流
├── app/                          # FastAPI 应用
│   ├── api/                      # API 路由
│   ├── models/                   # 数据模型
│   ├── schemas/                  # Pydantic 模式
│   ├── services/                 # 业务逻辑
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库连接
│   └── main.py                   # 应用入口
├── admin-frontend/               # Vue 3 管理后台
│   ├── src/                      # 前端源码
│   ├── dist/                     # 构建产物
│   └── package.json              # 前端依赖
├── migrations/                   # 数据库迁移
├── scripts/                      # 工具脚本
├── Dockerfile                    # Docker 镜像构建
├── docker-compose.yml            # Docker Compose 配置
├── .dockerignore                 # Docker 忽略文件
├── .gitignore                    # Git 忽略文件
├── .env.example                  # 环境变量模板
├── requirements.txt              # Python 依赖
└── README.md                     # 项目说明
```

---

## 🔧 环境变量说明

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | MySQL 连接字符串 | `mysql+pymysql://user:pass@localhost:3306/video` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `TMDB_API_KEY` | TMDB API 密钥 | `your_tmdb_api_key` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `your-secret-key-change-in-production` |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 访问令牌过期时间（分钟） | `1440` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 刷新令牌过期时间（天） | `7` |

---

## 📝 API 文档

启动服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

---

## 🔄 版本发布流程

### 发布新版本

```bash
# 1. 更新版本号（在 app/main.py 中）
# 2. 提交更改
git add .
git commit -m "chore: bump version to 2.1.0"

# 3. 创建标签
git tag -a v2.1.0 -m "Release version 2.1.0"

# 4. 推送标签
git push origin v2.1.0

# GitHub Actions 会自动构建并推送镜像：
# - ghcr.io/your-username/video-api:v2.1.0
# - ghcr.io/your-username/video-api:2.1
# - ghcr.io/your-username/video-api:2
```

---

## 🐛 故障排查

### Docker 构建失败

```bash
# 查看构建日志
docker-compose logs app

# 重新构建（不使用缓存）
docker-compose build --no-cache app
```

### GitHub Actions 失败

1. 检查 Actions 日志：仓库 → Actions → 点击失败的工作流
2. 常见问题：
   - **权限不足**：检查 Workflow permissions 设置
   - **镜像推送失败**：确认 GITHUB_TOKEN 权限
   - **构建超时**：检查 Dockerfile 优化

### 数据库连接失败

```bash
# 检查 MySQL 容器状态
docker-compose ps mysql

# 查看 MySQL 日志
docker-compose logs mysql

# 进入 MySQL 容器
docker-compose exec mysql mysql -u root -p
```

---

## 📚 相关资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Docker 文档](https://docs.docker.com/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

---

## 📄 许可证

请根据项目需求添加适当的许可证。

