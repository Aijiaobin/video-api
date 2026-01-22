# Video API - 快速启动指南

## 🚀 本地开发快速启动

### 方式一：使用 Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入真实配置

# 2. 启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f app

# 4. 访问服务
# API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 方式二：本地 Python 环境

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📦 GitHub 部署

### Windows 用户

```bash
# 运行部署脚本
deploy.bat
```

### Linux/Mac 用户

```bash
# 添加执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

### 手动部署

```bash
# 1. 初始化 Git（如果未初始化）
git init

# 2. 添加远程仓库
git remote add origin https://github.com/your-username/video-api.git

# 3. 提交并推送
git add .
git commit -m "feat: add Docker support and GitHub Actions CI/CD"
git branch -M main
git push -u origin main
```

---

## 🐳 使用 Docker 镜像

### 从 GitHub Container Registry 拉取

```bash
# 拉取最新镜像
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

## ⚙️ GitHub Actions 配置

推送代码后，需要在 GitHub 仓库中配置：

1. **启用 GitHub Actions**
   - Settings → Actions → General
   - 选择 "Allow all actions and reusable workflows"

2. **配置权限**
   - Settings → Actions → General → Workflow permissions
   - 选择 "Read and write permissions"
   - 勾选 "Allow GitHub Actions to create and approve pull requests"

3. **查看构建状态**
   - 进入 Actions 标签页
   - 查看工作流运行状态

4. **访问镜像**
   - 构建完成后，进入仓库 Packages 页面
   - 查看已发布的 Docker 镜像

---

## 📚 更多文档

详细部署文档请查看：[DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 🔧 常用命令

```bash
# Docker Compose
docker-compose up -d          # 启动服务
docker-compose down           # 停止服务
docker-compose logs -f app    # 查看日志
docker-compose restart app    # 重启应用
docker-compose ps             # 查看服务状态

# Docker
docker build -t video-api .   # 构建镜像
docker run -d -p 8000:8000 video-api  # 运行容器
docker logs -f video-api      # 查看日志
docker exec -it video-api sh  # 进入容器

# Git
git status                    # 查看状态
git add .                     # 添加所有文件
git commit -m "message"       # 提交更改
git push                      # 推送到远程
git tag v1.0.0                # 创建标签
git push origin v1.0.0        # 推送标签
```

---

## 🐛 故障排查

### 端口被占用

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Docker 构建失败

```bash
# 清理缓存重新构建
docker-compose build --no-cache app
```

### 数据库连接失败

```bash
# 检查 MySQL 容器
docker-compose ps mysql
docker-compose logs mysql

# 进入 MySQL 容器
docker-compose exec mysql mysql -u root -p
```

