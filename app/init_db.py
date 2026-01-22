"""数据库初始化脚本：创建默认角色、权限和管理员账号"""
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models.user import User, Role, Permission
from .core.security import get_password_hash


def init_permissions(db: Session):
    """初始化权限"""
    permissions_data = [
        # 分享权限
        {"name": "share:create", "display_name": "创建分享", "group": "share", "description": "允许用户提交新的分享链接"},
        {"name": "share:edit", "display_name": "编辑分享", "group": "share", "description": "允许编辑分享信息"},
        {"name": "share:delete", "display_name": "删除分享", "group": "share", "description": "允许删除分享"},
        {"name": "share:audit", "display_name": "审核分享", "group": "share", "description": "允许审核待审核的分享"},
        {"name": "share:scrape", "display_name": "触发刮削", "group": "share", "description": "允许触发元数据刮削"},
        {"name": "share:reparse", "display_name": "重新解析", "group": "share", "description": "允许重新解析分享链接"},
        {"name": "share:manage", "display_name": "管理分享", "group": "share", "description": "完整的分享管理权限"},
        # 用户权限
        {"name": "user:view", "display_name": "查看用户", "group": "user", "description": "允许查看用户列表和详情"},
        {"name": "user:create", "display_name": "创建用户", "group": "user", "description": "允许创建新用户"},
        {"name": "user:edit", "display_name": "编辑用户", "group": "user", "description": "允许编辑用户信息"},
        {"name": "user:delete", "display_name": "删除用户", "group": "user", "description": "允许删除用户"},
        {"name": "user:manage", "display_name": "管理用户", "group": "user", "description": "完整的用户管理权限"},
        # 角色权限
        {"name": "role:view", "display_name": "查看角色", "group": "role", "description": "允许查看角色列表"},
        {"name": "role:create", "display_name": "创建角色", "group": "role", "description": "允许创建新角色"},
        {"name": "role:edit", "display_name": "编辑角色", "group": "role", "description": "允许编辑角色信息"},
        {"name": "role:delete", "display_name": "删除角色", "group": "role", "description": "允许删除角色"},
        {"name": "role:assign", "display_name": "分配角色", "group": "role", "description": "允许为用户分配角色"},
        # 数据统计权限
        {"name": "stats:view", "display_name": "查看统计", "group": "stats", "description": "允许查看数据统计"},
        {"name": "stats:export", "display_name": "导出数据", "group": "stats", "description": "允许导出统计数据"},
        # 系统权限
        {"name": "system:config", "display_name": "系统配置", "group": "system", "description": "允许修改系统配置"},
        {"name": "system:version", "display_name": "版本管理", "group": "system", "description": "允许管理APP版本"},
        {"name": "system:announcement", "display_name": "公告管理", "group": "system", "description": "允许管理系统公告"},
    ]

    for perm_data in permissions_data:
        existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing:
            perm = Permission(**perm_data)
            db.add(perm)

    db.commit()
    print("✓ 权限初始化完成")


def init_roles(db: Session):
    """初始化角色"""
    # 获取所有权限
    all_permissions = db.query(Permission).all()
    share_permissions = [p for p in all_permissions if p.group == "share" and p.name in ["share:create", "share:delete"]]
    
    roles_data = [
        {
            "name": "admin",
            "display_name": "管理员",
            "description": "系统管理员，拥有所有权限",
            "is_system": True,
            "permissions": all_permissions
        },
        {
            "name": "user",
            "display_name": "普通用户",
            "description": "普通注册用户",
            "is_system": True,
            "permissions": share_permissions
        },
        {
            "name": "vip",
            "display_name": "VIP用户",
            "description": "VIP会员用户",
            "is_system": True,
            "permissions": share_permissions
        },
    ]
    
    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            permissions = role_data.pop("permissions", [])
            role = Role(**role_data)
            role.permissions = permissions
            db.add(role)
    
    db.commit()
    print("✓ 角色初始化完成")


def init_admin_user(db: Session, username: str = "admin", password: str = "admin123"):
    """初始化管理员账号"""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"✓ 管理员账号已存在: {username}")
        return
    
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    
    admin = User(
        username=username,
        password_hash=get_password_hash(password),
        nickname="系统管理员",
        user_type="admin",
        is_active=True,
        is_verified=True
    )
    
    if admin_role:
        admin.roles.append(admin_role)
    
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
        init_permissions(db)
        init_roles(db)
        init_admin_user(db)
        print("\n✓ 数据库初始化完成!")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

