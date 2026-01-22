"""
重新解析现有分享链接，填充 clean_title、sharer 等新字段
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.models import ShareLink, ShareFile, Sharer
from app.services.share_parser import tianyi_parser
from app.services.title_cleaner import title_cleaner, file_name_cleaner


async def reparse_share(db, share: ShareLink):
    """重新解析单个分享"""
    print(f"\n{'='*50}")
    print(f"解析分享 ID={share.id}: {share.share_url}")
    
    try:
        result = await tianyi_parser.parse_share(share.share_url, share.password)
        
        if not result:
            print(f"  [失败] 无法解析")
            return False
        
        # 更新分享信息
        share.raw_title = result.get("raw_title", "")
        share.clean_title = result.get("clean_title", "")
        share.share_type = result.get("share_type", "tv")
        share.share_code = result.get("share_code", "")
        
        print(f"  raw_title: {share.raw_title}")
        print(f"  clean_title: {share.clean_title}")
        print(f"  share_type: {share.share_type}")
        
        # 处理分享人
        sharer_info = result.get("sharer_info", {})
        if sharer_info and sharer_info.get("sharer_id"):
            sharer = db.query(Sharer).filter(
                Sharer.sharer_id == sharer_info["sharer_id"]
            ).first()
            
            if not sharer:
                sharer = Sharer(
                    sharer_id=sharer_info["sharer_id"],
                    nickname=sharer_info.get("nickname", ""),
                    avatar_url=sharer_info.get("avatar_url", ""),
                    drive_type=share.drive_type,
                    share_count=1
                )
                db.add(sharer)
                db.flush()
                print(f"  [新分享人] {sharer.nickname} ({sharer.sharer_id})")
            else:
                sharer.share_count += 1
                print(f"  [已有分享人] {sharer.nickname} ({sharer.sharer_id})")
            
            share.sharer_id = sharer.id
        
        # 更新现有文件的信息
        for db_file in share.files:
            file_info = file_name_cleaner.parse(db_file.file_name)
            db_file.clean_name = file_info["clean_name"]
            db_file.file_type = file_info["file_type"]
            db_file.season_number = file_info["season_number"]
            db_file.episode_number = file_info["episode_number"]
            db_file.resolution = file_info["resolution"]
            db_file.video_codec = file_info["video_codec"]
            db_file.audio_codec = file_info["audio_codec"]
        
        db.commit()
        print(f"  [成功] 已更新")
        return True
        
    except Exception as e:
        print(f"  [错误] {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    db = SessionLocal()
    
    try:
        # 获取所有需要重新解析的分享
        shares = db.query(ShareLink).filter(
            ShareLink.status == "active",
            ShareLink.drive_type == "tianyi"
        ).all()
        
        print(f"找到 {len(shares)} 个分享需要重新解析")
        
        success = 0
        failed = 0
        
        for share in shares:
            if await reparse_share(db, share):
                success += 1
            else:
                failed += 1
            
            # 避免请求过快
            await asyncio.sleep(1)
        
        print(f"\n{'='*50}")
        print(f"解析完成: 成功 {success}, 失败 {failed}")
        print(f"{'='*50}")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

