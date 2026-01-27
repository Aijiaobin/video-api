# TMDB 搜索类型修正功能

## 问题背景

TMDB 的 `movie` 和 `tv` 是两套独立的 ID 系统，同一个 ID（如 33422）在两个系统中代表完全不同的内容。

当系统自动判断的 `share_type` 错误时，即使手动指定了正确的 TMDB ID，也会因为查询了错误的接口（movie vs tv）而获取到错误的元数据。

## 解决方案

在分享编辑页面添加"媒体类型"下拉选择，允许用户手动修改 `share_type` 字段，从而修正错误的类型判断。

## 修改内容

### 后端修改

1. **`app/api/admin_shares.py`**
   - `EditTitleRequest` 添加 `share_type` 参数
   - `edit_share_title` 接口支持修改 `share_type` 字段

2. **`app/api/shares.py`**
   - `scrape_share_metadata` 函数直接使用 `share_type` 字段决定 TMDB 查询类型

### 前端修改

1. **`admin-frontend/src/views/Shares.vue`**
   - 编辑对话框添加"媒体类型"下拉选择（tv/movie/movie_collection）
   - 保存时同步更新 `share_type` 字段

2. **`admin-frontend/src/api/index.ts`**
   - `editTitle` 接口参数添加 `share_type`

## 使用方法

1. 在分享管理页面点击"编辑"按钮
2. 在"媒体类型"下拉框中选择正确的类型：
   - **剧集 (tv)**: 使用 TMDB 的 `/tv/{id}` 接口
   - **电影 (movie)**: 使用 TMDB 的 `/movie/{id}` 接口
   - **电影合集**: 特殊处理，刮削每个视频文件
3. 如需要，同时填写正确的 TMDB ID
4. 点击"保存并重新刮削"

## 刮削逻辑

```
媒体类型: share_type 字段（可通过编辑页面手动修改）
  - tv → 调用 TMDB /tv/{id} 接口
  - movie/movie_collection → 调用 TMDB /movie/{id} 接口

TMDB ID 优先级:
  1. manual_tmdb_id（手动指定）
  2. extracted_tmdb_id（从标题提取）
  3. 使用标题搜索 TMDB
```

## 无需数据库迁移

本次修改直接复用现有的 `share_type` 字段，无需新增数据库字段。

