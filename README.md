# Video Share API

影视分享广场 & 元数据刮削服务后端

## 启动

```bash
cd video-api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动后访问: http://localhost:8000/docs

## 环境变量

复制 `.env` 文件并配置:
- `DATABASE_URL`: MySQL 连接字符串
- `TMDB_API_KEY`: TMDB API 密钥
