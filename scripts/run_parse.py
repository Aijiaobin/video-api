import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import asyncio
from app.database import SessionLocal
from app.models.models import ShareLink
from app.api.shares import parse_and_update_share

async def main():
    db = SessionLocal()
    shares = db.query(ShareLink).filter(
        ShareLink.status != 'deleted',
        (ShareLink.clean_title == None) | (ShareLink.clean_title == '')
    ).all()
    
    total = len(shares)
    print(f'[START] Parsing {total} shares with 5 threads', flush=True)
    db.close()
    
    if total == 0:
        print('No shares to parse', flush=True)
        return
    
    semaphore = asyncio.Semaphore(5)
    success = 0
    failed = 0
    
    async def parse_one(idx, s):
        nonlocal success, failed
        async with semaphore:
            try:
                await parse_and_update_share(s.id, s.share_url, s.password, s.drive_type)
                success += 1
            except Exception as e:
                failed += 1
            if (idx + 1) % 50 == 0:
                print(f'Progress: {idx+1}/{total} (ok:{success} fail:{failed})', flush=True)
            await asyncio.sleep(0.2)
    
    await asyncio.gather(*[parse_one(i, s) for i, s in enumerate(shares)])
    print(f'[DONE] Success: {success}, Failed: {failed}', flush=True)

if __name__ == '__main__':
    asyncio.run(main())

