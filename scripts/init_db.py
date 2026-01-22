"""数据库初始化脚本 - 创建默认管理员用户"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import get_password_hash


def init_database():
    """初始化数据库"""
    print("🔧 开始初始化数据库...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")
    
    db = SessionLocal()
    try:
        # 检查是否已存在管理员
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("⚠️  管理员用户已存在，跳过创建")
            print(f"   用户名: {existing_admin.username}")
            print(f"   用户类型: {existing_admin.user_type}")
            print(f"   ID: {existing_admin.id}")
            return
        
        # 创建默认管理员
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            email="admin@example.com",
            nickname="系统管理员",
            user_type="admin",
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ 默认管理员创建成功")
        print(f"   用户名: admin")
        print(f"   密码: admin123")
        print(f"   邮箱: admin@example.com")
        print(f"   用户类型: admin")
        print(f"   ID: {admin_user.id}")
        print("")
        print("⚠️  重要提示：请立即登录并修改默认密码！")
        print("   登录后访问: /auth/change-password")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()

