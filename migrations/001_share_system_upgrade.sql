-- =====================================================
-- 数据库迁移脚本 - 网盘影视库架构升级
-- 执行前请备份数据库！
-- =====================================================

-- 1. 创建分享人表
CREATE TABLE IF NOT EXISTS sharers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sharer_id VARCHAR(100) NOT NULL UNIQUE,
    nickname VARCHAR(255),
    avatar_url VARCHAR(500),
    drive_type VARCHAR(50) NOT NULL,
    share_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sharer_id (sharer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 2. 修改 share_links 表
-- 2.1 添加新字段
ALTER TABLE share_links
    ADD COLUMN share_code VARCHAR(100) AFTER share_url,
    ADD COLUMN raw_title VARCHAR(500) AFTER password,
    ADD COLUMN clean_title VARCHAR(255) AFTER raw_title,
    ADD COLUMN share_type VARCHAR(50) DEFAULT 'tv' AFTER clean_title,
    ADD COLUMN media_id INT AFTER share_type,
    ADD COLUMN sharer_id INT AFTER poster_url,
    ADD COLUMN last_check_at DATETIME AFTER status;

-- 2.2 迁移旧数据: title -> raw_title
UPDATE share_links SET raw_title = title WHERE title IS NOT NULL;

-- 2.3 添加索引
ALTER TABLE share_links
    ADD INDEX idx_share_code (share_code),
    ADD INDEX idx_share_type (share_type),
    ADD INDEX idx_media_id (media_id),
    ADD INDEX idx_sharer_id (sharer_id);

-- 2.4 添加外键约束
ALTER TABLE share_links
    ADD CONSTRAINT fk_share_links_media FOREIGN KEY (media_id) REFERENCES media_metadata(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_share_links_sharer FOREIGN KEY (sharer_id) REFERENCES sharers(id) ON DELETE SET NULL;

-- 2.5 删除旧字段 (可选，建议确认数据迁移完成后再执行)
-- ALTER TABLE share_links DROP COLUMN title;
-- ALTER TABLE share_links DROP COLUMN tmdb_id;
-- ALTER TABLE share_links DROP COLUMN uploader_id;


-- 3. 修改 share_files 表
-- 3.1 添加新字段
ALTER TABLE share_files
    ADD COLUMN clean_name VARCHAR(500) AFTER file_name,
    ADD COLUMN file_type VARCHAR(50) DEFAULT 'other' AFTER parent_id,
    ADD COLUMN season_number INT AFTER file_type,
    ADD COLUMN episode_number INT AFTER season_number,
    ADD COLUMN media_id INT AFTER episode_number,
    ADD COLUMN poster_url VARCHAR(500) AFTER media_id,
    ADD COLUMN resolution VARCHAR(20) AFTER poster_url,
    ADD COLUMN video_codec VARCHAR(20) AFTER resolution,
    ADD COLUMN audio_codec VARCHAR(20) AFTER video_codec;

-- 3.2 添加索引
ALTER TABLE share_files
    ADD INDEX idx_file_type (file_type),
    ADD INDEX idx_season_episode (season_number, episode_number),
    ADD INDEX idx_media_id (media_id);

-- 3.3 添加外键约束
ALTER TABLE share_files
    ADD CONSTRAINT fk_share_files_media FOREIGN KEY (media_id) REFERENCES media_metadata(id) ON DELETE SET NULL;


-- =====================================================
-- 数据迁移：处理现有数据
-- =====================================================

-- 4. 更新现有文件的 file_type (根据扩展名判断)
UPDATE share_files 
SET file_type = 'video' 
WHERE file_name REGEXP '\\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v|ts|rmvb)$';

UPDATE share_files 
SET file_type = 'subtitle' 
WHERE file_name REGEXP '\\.(srt|ass|ssa|sub|idx|vtt)$';

UPDATE share_files 
SET file_type = 'audio' 
WHERE file_name REGEXP '\\.(mp3|flac|wav|aac|m4a|ogg|wma)$';

UPDATE share_files 
SET file_type = 'image' 
WHERE file_name REGEXP '\\.(jpg|jpeg|png|gif|bmp|webp)$';


-- =====================================================
-- 验证迁移结果
-- =====================================================
-- SELECT COUNT(*) as total_sharers FROM sharers;
-- SELECT COUNT(*) as shares_with_raw_title FROM share_links WHERE raw_title IS NOT NULL;
-- SELECT file_type, COUNT(*) as count FROM share_files GROUP BY file_type;

