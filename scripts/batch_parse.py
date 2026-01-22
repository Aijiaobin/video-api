"""
批量解析分享链接并刮削元数据
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

import asyncio
from app.database import SessionLocal
from app.models.models import ShareLink
from app.api.shares import parse_and_update_share


async def main():
    db = SessionLocal()
    
    # Get shares without metadata
    shares = db.query(ShareLink).filter(
        ShareLink.status == 'active',
        ShareLink.media_id == None
    ).all()
    
    total = len(shares)
    print(f'Shares to parse: {total}', flush=True)
    db.close()
    
    success = 0
    failed = 0
    
    for i, share in enumerate(shares):
        try:
            await parse_and_update_share(
                share.id,
                share.share_url,
                share.password,
                share.drive_type
            )
            success += 1
        except Exception as e:
            failed += 1
            err_msg = str(e)
            if len(err_msg) > 50:
                err_msg = err_msg[:50] + '...'
            print(f'[{i+1}] Error: {err_msg}', flush=True)
        
        if (i + 1) % 50 == 0:
            print(f'Progress: {i+1}/{total} (success: {success}, failed: {failed})', flush=True)
        
        # Small delay
        if (i + 1) % 5 == 0:
            await asyncio.sleep(0.3)
    
    print(f'\n=== Parse Complete ===', flush=True)
    print(f'Total: {total}', flush=True)
    print(f'Success: {success}', flush=True)
    print(f'Failed: {failed}', flush=True)


if __name__ == '__main__':
    asyncio.run(main())

