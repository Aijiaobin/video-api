"""
批量导入分享链接脚本
从分享链接.txt文件中提取链接并导入到数据库
"""
import asyncio
import re
import sys
import os

# 设置 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.models import ShareLink
from app.api.shares import parse_and_update_share


def extract_shares_from_file(file_path: str) -> list:
    """从文件中提取分享链接和访问码"""
    shares = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按行处理
    lines = content.split('\n')
    current_title = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 跳过日期行
        if re.match(r'^\d{4}\.\d{1,2}\.\d{1,2}$', line):
            continue
        
        # 检测链接行
        link_match = re.search(r'链接[：:]\s*(https?://cloud\.189\.cn/t/[a-zA-Z0-9]+)', line)
        if link_match:
            share_url = link_match.group(1)
            
            # 查找访问码（可能在同一行或下一行）
            password = None
            # 同一行
            pwd_match = re.search(r'访问码[：:]\s*([a-zA-Z0-9]{3,6})', line)
            if pwd_match:
                password = pwd_match.group(1)
            # 下一行
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                pwd_match = re.search(r'访问码[：:]\s*([a-zA-Z0-9]{3,6})', next_line)
                if pwd_match:
                    password = pwd_match.group(1)
            
            # 获取标题（链接行的上一行，如果不是日期或空行）
            if i > 0:
                prev_line = lines[i - 1].strip()
                if prev_line and not prev_line.startswith('链接') and not re.match(r'^\d{4}\.\d{1,2}\.\d{1,2}$', prev_line):
                    current_title = prev_line
            
            shares.append({
                'url': share_url,
                'password': password,
                'title': current_title
            })
    
    return shares


async def import_share(db, share_url: str, password: str = None) -> dict:
    """导入单个分享"""
    try:
        # 检查是否已存在
        existing = db.query(ShareLink).filter(ShareLink.share_url == share_url).first()
        if existing:
            return {
                'url': share_url,
                'status': 'duplicate',
                'message': '链接已存在',
                'share_id': existing.id
            }
        
        # 创建分享记录
        share = ShareLink(
            drive_type='tianyi',
            share_url=share_url,
            password=password,
            status='active'  # 直接设为活跃状态
        )
        db.add(share)
        db.flush()
        
        # 解析并刮削
        await parse_and_update_share(
            share.id,
            share_url,
            password,
            'tianyi'
        )
        
        db.commit()
        
        return {
            'url': share_url,
            'status': 'success',
            'message': '导入成功',
            'share_id': share.id
        }
        
    except Exception as e:
        db.rollback()
        return {
            'url': share_url,
            'status': 'failed',
            'message': str(e)
        }


async def main():
    # 读取分享链接文件
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '分享链接.txt')
    
    print(f"读取文件: {file_path}")
    shares = extract_shares_from_file(file_path)
    print(f"共提取到 {len(shares)} 个分享链接")
    
    # 统计
    success = 0
    failed = 0
    duplicates = 0
    expired = 0
    
    db = SessionLocal()
    
    try:
        for i, share in enumerate(shares):
            print(f"\n[{i+1}/{len(shares)}] 处理: {share['url']}")
            if share.get('title'):
                print(f"  标题: {share['title'][:50]}...")
            
            result = await import_share(db, share['url'], share.get('password'))
            
            if result['status'] == 'success':
                success += 1
                print(f"  [OK] Import success (ID: {result.get('share_id')})")
            elif result['status'] == 'duplicate':
                duplicates += 1
                print(f"  [SKIP] Already exists (ID: {result.get('share_id')})")
            elif 'expired' in result.get('message', '').lower() or '过期' in result.get('message', '') or '不存在' in result.get('message', ''):
                expired += 1
                print(f"  [EXPIRED] Link expired or not found: {result['message']}")
            else:
                failed += 1
                print(f"  [FAIL] Error: {result['message']}")
            
            # 每处理50个暂停一下，避免请求过快
            if (i + 1) % 50 == 0:
                print(f"\n--- 已处理 {i+1} 个，暂停2秒 ---")
                await asyncio.sleep(2)
    
    finally:
        db.close()
    
    print(f"\n{'='*50}")
    print(f"导入完成!")
    print(f"  成功: {success}")
    print(f"  重复: {duplicates}")
    print(f"  过期/不存在: {expired}")
    print(f"  失败: {failed}")
    print(f"  总计: {len(shares)}")


if __name__ == '__main__':
    asyncio.run(main())

