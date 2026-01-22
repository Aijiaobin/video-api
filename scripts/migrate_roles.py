"""角色迁移脚本 - 将Role表数据迁移到user_type"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.user import User


def check_old_tables_exist(db: Session) -> bool:
    """检查旧的角色表是否存在"""
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='roles'"))
        return result.fetchone() is not None
    except Exception:
        return False


def migrate_roles():
    """迁移角色到用户类型"""
    db = SessionLocal()
    try:
        print("🔄 开始迁移用户角色...")
        
        # 检查是否存在旧的角色表
        if not check_old_tables_exist(db):
            print("⚠️  未发现旧的角色表，可能已经迁移过或使用新架构")
            print("   跳过迁移步骤")
            return
        
        # 查询所有用户
        users = db.query(User).all()
        migrated_count = 0
        skipped_count = 0
        
        for user in users:
            # 如果用户已经有正确的user_type，跳过
            if user.user_type in ['admin', 'vip', 'user']:
                skipped_count += 1
                continue
            
            # 尝试从角色关联表获取角色信息
            try:
                # 查询用户的角色
                result = db.execute(text("""
                    SELECT r.name FROM roles r
                    JOIN user_roles ur ON r.id = ur.role_id
                    WHERE ur.user_id = :user_id
                """), {"user_id": user.id})
                
                role_names = [row[0] for row in result.fetchall()]
                
                # 根据角色设置user_type（优先级：admin > vip > user）
                if 'admin' in role_names:
                    user.user_type = 'admin'
                elif 'vip' in role_names:
                    user.user_type = 'vip'
                else:
                    user.user_type = 'user'
                
                migrated_count += 1
                print(f"   ✓ 用户 {user.username} (ID:{user.id}) → {user.user_type}")
                
            except Exception as e:
                # 如果查询失败，设置为默认的普通用户
                user.user_type = 'user'
                migrated_count += 1
                print(f"   ⚠ 用户 {user.username} (ID:{user.id}) → user (默认)")
        
        db.commit()
        
        print(f"\n✅ 迁移完成")
        print(f"   - 已迁移: {migrated_count} 个用户")
        print(f"   - 已跳过: {skipped_count} 个用户")
        print(f"   - 总计: {len(users)} 个用户")
        
        # 提示下一步操作
        print(f"\n📝 下一步操作：")
        print(f"   1. 验证迁移结果")
        print(f"   2. 备份旧表数据（可选）")
        print(f"   3. 删除旧表（谨慎操作）")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def drop_old_tables():
    """删除旧的角色相关表（谨慎操作）"""
    print("\n⚠️  警告：即将删除旧的角色表")
    print("   这个操作不可逆！请确保已经备份数据")
    
    response = input("   确认删除？(输入 'YES' 继续): ")
    if response != 'YES':
        print("   已取消删除操作")
        return
    
    db = SessionLocal()
    try:
        print("\n🗑️  开始删除旧表...")
        
        # 删除关联表
        db.execute(text("DROP TABLE IF EXISTS user_roles"))
        print("   ✓ 删除 user_roles 表")
        
        db.execute(text("DROP TABLE IF EXISTS role_permissions"))
        print("   ✓ 删除 role_permissions 表")
        
        # 删除主表
        db.execute(text("DROP TABLE IF EXISTS roles"))
        print("   ✓ 删除 roles 表")
        
        db.execute(text("DROP TABLE IF EXISTS permissions"))
        print("   ✓ 删除 permissions 表")
        
        db.commit()
        print("\n✅ 旧表删除完成")
        
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='角色迁移脚本')
    parser.add_argument('--drop-old-tables', action='store_true', 
                       help='删除旧的角色表（谨慎操作）')
    
    args = parser.parse_args()
    
    # 执行迁移
    migrate_roles()
    
    # 如果指定了删除旧表
    if args.drop_old_tables:
        drop_old_tables()

