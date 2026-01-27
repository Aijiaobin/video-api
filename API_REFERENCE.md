# Video Share API 接口文档

## 概述

本项目基于 **FastAPI** 构建，提供影视资源分享、元数据刮削、用户管理及系统配置等核心功能。

*   **基础 URL**: `/api`
*   **认证方式**: Bearer Token (JWT)

---

## 1. 认证模块 (`/auth`)

处理用户注册、登录及令牌刷新。

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | 用户注册 | 公开 |
| `POST` | `/auth/login` | 用户登录 (获取 Access Token) | 公开 |
| `POST` | `/auth/refresh` | 刷新 Token | 已登录 |
| `GET` | `/auth/me` | 获取当前用户信息 | 已登录 |

#### 请求体示例

**POST /auth/register**
```json
{
  "username": "user123",
  "password": "securepassword",
  "email": "user@example.com"
}
```

**POST /auth/login**
```json
{
  "username": "user123",
  "password": "securepassword"
}
```

**POST /auth/refresh**
```json
{
  "refresh_token": "your_refresh_token_here"
}
```

---

## 2. 分享广场 (`/shares`)

用户侧的影视分享资源管理。

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/shares` | 获取分享列表 (支持搜索/筛选) | 公开/已登录 |
| `POST` | `/shares` | 创建新的分享 | 已登录 |
| `GET` | `/shares/{id}` | 获取分享详情 | 公开/已登录 |
| `PUT` | `/shares/{id}` | 更新分享信息 | 作者/管理员 |
| `DELETE` | `/shares/{id}` | 删除分享 | 作者/管理员 |
| `POST` | `/shares/{id}/save` | 保存/转存分享 (如转存到个人网盘) | 已登录 |
| `POST` | `/shares/{id}/report` | 举报分享 | 已登录 |

#### 请求体示例

**POST /shares (创建分享)**
```json
{
  "share_url": "https://www.aliyundrive.com/s/xxxxxxxx",
  "password": "abcd",  // 可选
  "drive_type": "aliyun", // tianyi, aliyun, quark
  "title": "可选的自定义标题", // 可选
  "content": "可选的描述信息" // 可选
}
```

**PUT /shares/{id} (更新分享)**
```json
{
  "title": "新标题",
  "content": "更新后的描述"
}
```

**POST /shares/{id}/save (转存)**
```json
{
  "target_drive_id": "root", // 目标文件夹ID，默认为root
  "drive_token": "optional_access_token" // 如果需要特定网盘的token
}
```

**POST /shares/{id}/report (举报)**
```json
{
  "reason": "invalid_link", // invalid_link, pornography, violence, other
  "description": "链接已失效，请处理"
}
```

---

## 3. 元数据服务 (`/metadata`)

集成 TMDB API，提供影视信息查询与刮削。

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/metadata/search` | 搜索影视元数据 (关键词) | 已登录 |
| `GET` | `/metadata/{tmdb_id}` | 根据 TMDB ID 获取详细信息 | 已登录 |
| `POST` | `/metadata/scrape` | 主动触发/更新刮削任务 | 管理员 |

#### 请求体示例

**GET /metadata/search (Query Params)**
*   `title`: "Inception"
*   `year`: 2010 (可选)
*   `media_type`: "movie" (可选, movie/tv)

**POST /metadata/scrape**
```json
{
  "tmdb_id": 27205,
  "media_type": "movie",
  "force_update": true
}
```

---

## 4. 管理后台 - 用户管理 (`/admin/users`)

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/users` | 获取用户列表 | 管理员 |
| `GET` | `/admin/users/{id}` | 获取特定用户详情 | 管理员 |
| `PUT` | `/admin/users/{id}` | 更新用户信息 (如封禁/解封) | 管理员 |
| `DELETE` | `/admin/users/{id}` | 删除用户 | 超级管理员 |

#### 请求体示例

**PUT /admin/users/{id}**
```json
{
  "role": "vip", // user, vip, admin
  "status": "active", // active, banned
  "remark": "VIP member"
}
```

---

## 5. 管理后台 - 分享管理 (`/admin/shares`)

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/shares` | 获取所有分享 (含已删除/待审核) | 管理员 |
| `POST` | `/admin/shares/{id}/audit` | 审核分享 (通过/拒绝) | 管理员 |

#### 请求体示例

**POST /admin/shares/{id}/audit**
```json
{
  "status": "approved", // approved, rejected
  "reason": "Content follows guidelines" // 如果拒绝，需填写理由
}
```

---

## 6. 管理后台 - 系统统计 (`/admin/stats`)

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/stats/overview` | 获取系统概览数据 (用户数/分享数等) | 管理员 |
| `GET` | `/admin/stats/daily` | 获取每日活跃数据 | 管理员 |

---

## 7. 管理后台 - 系统配置 (`/admin/system`)

动态管理后端配置，无需重启服务。

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/system/config` | 获取当前系统配置 | 管理员 |
| `PUT` | `/admin/system/config` | 更新系统配置 (如 TMDB Key, 公告等) | 超级管理员 |

#### 请求体示例

**PUT /admin/system/config**
```json
{
  "tmdb_api_key": "new_api_key_xxxxxxxx",
  "announcement": "System maintenance at 00:00",
  "enable_registration": true,
  "default_user_role": "user"
}
```

---

## 8. 版本管理 (`/admin/versions`)

管理客户端 APP 的更新检查。

| 方法 | 路径 | 描述 | 权限 |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/versions/latest` | 获取最新版本信息 | 公开 |
| `POST` | `/admin/versions` | 发布新版本 | 管理员 |
| `PUT` | `/admin/versions/{id}` | 更新版本信息 | 管理员 |

#### 请求体示例

**POST /admin/versions**
```json
{
  "version_code": 102,
  "version_name": "1.0.2",
  "changelog": "Fix bugs and improve performance",
  "download_url": "https://example.com/app-v1.0.2.apk",
  "force_update": false
}
```

---

## 数据模型简述

### User (用户)
*   `id`: UUID
*   `username`: 用户名
*   `role`: 角色 (user, vip, admin, super_admin)
*   `status`: 状态 (active, banned)

### Share (分享)
*   `id`: UUID
*   `title`: 标题
*   `content`: 描述/内容
*   `urls`: 资源链接列表 (JSON)
*   `tmdb_id`: 关联的 TMDB ID
*   `media_type`: 媒体类型 (movie, tv)
*   `user_id`: 发布者 ID
*   `views`: 浏览量
*   `saves`:以此保存量

### Metadata (元数据缓存)
*   `tmdb_id`: TMDB ID (主键)
*   `data`: 完整的 JSON 数据 (包含海报、简介等)
*   `updated_at`: 最后更新时间

