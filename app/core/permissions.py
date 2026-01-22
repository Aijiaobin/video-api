"""权限配置 - 基于用户类型的权限定义"""
from typing import Set, Dict

# 普通用户权限（7个基础权限）
USER_PERMISSIONS: Set[str] = {
    "share:view",           # 查看分享广场
    "share:create",         # 创建分享
    "share:delete_own",     # 删除自己的分享
    "share:save",           # 转存分享
    "user:view_own",        # 查看自己的信息
    "user:update_own",      # 修改自己的信息
    "stats:view_own",       # 查看自己的统计
}

# VIP用户权限（15个 = 7基础 + 8扩展）
VIP_PERMISSIONS: Set[str] = USER_PERMISSIONS | {
    "share:priority",       # 分享优先展示
    "share:batch_create",   # 批量创建分享
    "share:export",         # 导出分享数据
    "share:reparse",        # 重新解析分享
    "share:audit_own",      # 审核自己的分享
    "stats:view_advanced",  # 查看高级统计
    "api:rate_limit_high",  # 更高的API调用频率
    "feature:ad_free",      # 无广告
}

# 管理员权限（所有权限）
ADMIN_PERMISSIONS: Set[str] = {"*:*"}  # 通配符表示所有权限

# 用户类型到权限的映射
USER_TYPE_PERMISSIONS: Dict[str, Set[str]] = {
    "user": USER_PERMISSIONS,
    "vip": VIP_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
}


def get_user_permissions(user_type: str) -> Set[str]:
    """获取用户类型对应的权限集合"""
    return USER_TYPE_PERMISSIONS.get(user_type, set())


def has_permission(user_type: str, permission: str) -> bool:
    """检查用户类型是否拥有指定权限
    
    Args:
        user_type: 用户类型 (user/vip/admin)
        permission: 权限名称 (如 share:create)
    
    Returns:
        bool: 是否拥有权限
    """
    permissions = get_user_permissions(user_type)
    
    # 管理员拥有所有权限
    if "*:*" in permissions:
        return True
    
    # 精确匹配
    if permission in permissions:
        return True
    
    # 通配符匹配（如 share:* 匹配 share:view）
    permission_parts = permission.split(":")
    if len(permission_parts) == 2:
        wildcard = f"{permission_parts[0]}:*"
        if wildcard in permissions:
            return True
    
    return False


def list_all_permissions() -> Dict[str, list]:
    """列出所有权限（按用户类型分组）"""
    return {
        "user": sorted(list(USER_PERMISSIONS)),
        "vip": sorted(list(VIP_PERMISSIONS)),
        "admin": ["*:*"]
    }

