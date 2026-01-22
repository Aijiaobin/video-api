"""数据库初始化脚本 - 创建默认管理员用户"""
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models.user import User
from .core.security import get_password_hash


def init_admin_user(db: Session, username: str = "admin", password: str = "admin123"):
    """初始化管理员账号"""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"✓ 管理员账号已存在: {username}")
        return

    admin = User(
        username=username,
        password_hash=get_password_hash(password),
        email="admin@example.com",
        nickname="系统管理员",
        user_type="admin",
        is_active=True,
        is_verified=True
    )

    db.add(admin)
    db.commit()
    print(f"✓ 管理员账号创建成功: {username} / {password}")


def init_db():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建完成")

    db = SessionLocal()
    try:
        init_admin_user(db)
        print("\n✓ 数据库初始化完成!")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

