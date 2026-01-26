-- =====================================================
-- 数据库迁移脚本 - 添加手动标题和TMDB ID字段
-- 版本: 002
-- 日期: 2026-01-26
-- 说明: 支持手动修正标题和TMDB ID，以及从标题提取TMDB ID
-- 数据库: SQLite
-- =====================================================

-- 1. 为 share_links 表添加新字段
-- SQLite 不支持一次添加多列，需要分开执行
ALTER TABLE share_links ADD COLUMN manual_title VARCHAR(255);
ALTER TABLE share_links ADD COLUMN manual_tmdb_id INTEGER;
ALTER TABLE share_links ADD COLUMN extracted_tmdb_id INTEGER;

-- 2. 添加索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_manual_tmdb_id ON share_links(manual_tmdb_id);
CREATE INDEX IF NOT EXISTS idx_extracted_tmdb_id ON share_links(extracted_tmdb_id);

-- =====================================================
-- 使用说明
-- =====================================================
-- 
-- 标题优先级：
-- 1. manual_title（手动修正）- 最高优先级
-- 2. clean_title（自动清洗）- 默认使用
-- 
-- TMDB ID 优先级：
-- 1. manual_tmdb_id（手动指定）- 最高优先级
-- 2. extracted_tmdb_id（从标题提取，如 {tmdb 156201}）
-- 3. 使用标题搜索TMDB
-- 
-- 示例：
-- - 标题 "滚滚红尘 {tmdb 156201}" 会自动提取 extracted_tmdb_id = 156201
-- - 管理员可以手动设置 manual_title = "正确的标题"
-- - 管理员可以手动设置 manual_tmdb_id = 123456
-- 
-- =====================================================
-- 验证迁移结果
-- =====================================================
-- 
-- 查看表结构：
-- DESCRIBE share_links;
-- 
-- 查看索引：
-- SHOW INDEX FROM share_links;
-- 
-- =====================================================

