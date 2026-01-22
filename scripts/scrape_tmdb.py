"""
为现有分享刮削 TMDB 元数据
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.models import ShareLink, MediaMetadata
from app.services.tmdb_service import TMDBService


async def scrape_share(db, tmdb_service: TMDBService, share: ShareLink):
    """为单个分享刮削 TMDB 元数据"""
    print(f"\n{'='*50}")
    print(f"刮削分享 ID={share.id}: {share.clean_title}")
    print(f"  类型: {share.share_type}")
    
    # 跳过电影合集（需要单独处理每个子文件夹）
    if share.share_type == "movie_collection":
        print(f"  [跳过] 电影合集需要单独刮削子文件夹")
        return False
    
    # 跳过已有元数据的
    if share.media_id:
        print(f"  [跳过] 已有元数据 media_id={share.media_id}")
        return True
    
    # 确定 TMDB 媒体类型
    media_type = "tv" if share.share_type == "tv" else "movie"
    
    try:
        # 搜索并缓存
        metadata = await tmdb_service.search_and_cache(
            title=share.clean_title,
            year=None,  # 暂不使用年份
            media_type=media_type
        )
        
        if metadata:
            # 更新分享记录
            share.media_id = metadata.id
            share.poster_url = metadata.poster_url
            db.commit()
            
            print(f"  [成功] 匹配到: {metadata.title} ({metadata.year})")
            print(f"  TMDB ID: {metadata.tmdb_id}")
            print(f"  评分: {metadata.rating}")
            print(f"  海报: {metadata.poster_url}")
            return True
        else:
            print(f"  [失败] 未找到匹配的 TMDB 记录")
            return False
            
    except Exception as e:
        print(f"  [错误] {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    db = SessionLocal()
    tmdb_service = TMDBService(db)
    
    try:
        # 获取所有需要刮削的分享（排除电影合集）
        shares = db.query(ShareLink).filter(
            ShareLink.status == "active",
            ShareLink.media_id == None,
            ShareLink.share_type.in_(["tv", "movie"])
        ).all()
        
        print(f"找到 {len(shares)} 个分享需要刮削 TMDB 元数据")
        
        success = 0
        failed = 0
        
        for share in shares:
            if await scrape_share(db, tmdb_service, share):
                success += 1
            else:
                failed += 1
            
            # 避免请求过快（TMDB 有速率限制）
            await asyncio.sleep(0.5)
        
        print(f"\n{'='*50}")
        print(f"刮削完成: 成功 {success}, 失败 {failed}")
        print(f"{'='*50}")
        
        # 显示已缓存的元数据统计
        total_metadata = db.query(MediaMetadata).count()
        print(f"\n元数据缓存总数: {total_metadata}")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

