-- 修改 media_metadata 表的唯一约束
-- TMDB 的 movie 和 tv 是两套独立的 ID 系统，同一个 tmdb_id 可能对应不同的 media_type
-- 需要将 tmdb_id 的单独唯一约束改为 (tmdb_id, media_type) 的联合唯一约束

-- SQLite 不支持直接修改约束，需要重建表
-- 由于有外键关联（tv_seasons -> media_metadata），需要先处理关联表

-- 关闭外键约束检查
PRAGMA foreign_keys=OFF;

-- 开始事务
BEGIN TRANSACTION;

-- 1. 创建新的 media_metadata 表（带正确的约束）
CREATE TABLE IF NOT EXISTS media_metadata_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER NOT NULL,
    media_type VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    original_title VARCHAR(255),
    year INTEGER,
    poster_url VARCHAR(500),
    backdrop_url VARCHAR(500),
    plot TEXT,
    rating FLOAT,
    runtime INTEGER,
    genres TEXT,
    status VARCHAR(50),
    total_seasons INTEGER,
    total_episodes INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tmdb_id, media_type)
);

-- 2. 复制数据（保持 id 不变以维护外键关系）
INSERT OR IGNORE INTO media_metadata_new
SELECT * FROM media_metadata;

-- 3. 删除旧表
DROP TABLE IF EXISTS media_metadata;

-- 4. 重命名新表
ALTER TABLE media_metadata_new RENAME TO media_metadata;

-- 5. 重建索引
CREATE INDEX IF NOT EXISTS ix_media_metadata_tmdb_id ON media_metadata (tmdb_id);
CREATE INDEX IF NOT EXISTS ix_media_metadata_year ON media_metadata (year);

-- 提交事务
COMMIT;

-- 重新开启外键约束检查
PRAGMA foreign_keys=ON;


