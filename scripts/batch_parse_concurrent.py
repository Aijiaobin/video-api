"""
批量解析分享链接 - 多线程版本
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from app.database import SessionLocal
from app.models.models import ShareLink
from app.api.shares import parse_and_update_share


async def batch_parse_concurrent(max_workers: int = 5):
    """多线程并发解析分享"""
    db = SessionLocal()
    
    # 获取所有未解析的分享
    shares = db.query(ShareLink).filter(
        ShareLink.status != 'deleted',
        (ShareLink.clean_title == None) | (ShareLink.clean_title == '')
    ).all()
    
    total = len(shares)
    print(f'[{datetime.now()}] Starting batch parse: {total} shares ({max_workers} threads)', flush=True)
    db.close()
    
    if total == 0:
        print('No shares to parse', flush=True)
        return
    
    semaphore = asyncio.Semaphore(max_workers)
    success = 0
    failed = 0
    
    async def parse_with_semaphore(idx, share_id, share_url, password, drive_type):
        nonlocal success, failed
        async with semaphore:
            try:
                await parse_and_update_share(share_id, share_url, password, drive_type)
                success += 1
                if (idx + 1) % 50 == 0:
                    print(f'[{datetime.now()}] Progress: {idx+1}/{total} (success: {success}, failed: {failed})', flush=True)
            except Exception as e:
                failed += 1
                err = str(e)[:50]
                print(f'[{datetime.now()}] Error share {share_id}: {err}', flush=True)
            await asyncio.sleep(0.2)
    
    # 创建所有任务
    tasks = [
        parse_with_semaphore(i, s.id, s.share_url, s.password, s.drive_type)
        for i, s in enumerate(shares)
    ]
    
    # 并发执行
    await asyncio.gather(*tasks)
    
    print(f'[{datetime.now()}] Batch parse completed!', flush=True)
    print(f'Total: {total}, Success: {success}, Failed: {failed}', flush=True)


if __name__ == '__main__':
    threads = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    asyncio.run(batch_parse_concurrent(threads))

