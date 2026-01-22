import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserInfo, type TokenResponse } from '@/api'

const TOKEN_KEY = 'admin_token'
const REFRESH_TOKEN_KEY = 'admin_refresh_token'
const USER_KEY = 'admin_user'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const refreshToken = ref<string>(localStorage.getItem(REFRESH_TOKEN_KEY) || '')
  const userInfo = ref<UserInfo | null>(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.user_type === 'admin')
  const isVip = computed(() => userInfo.value?.user_type === 'vip' || isAdmin.value)  // ✅ VIP或管理员
  const userType = computed(() => userInfo.value?.user_type || '')  // ✅ 导出userType
  const username = computed(() => userInfo.value?.username || '')
  const nickname = computed(() => userInfo.value?.nickname || userInfo.value?.username || '')

  function setToken(tokenData: TokenResponse) {
    token.value = tokenData.access_token
    refreshToken.value = tokenData.refresh_token
    localStorage.setItem(TOKEN_KEY, tokenData.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, tokenData.refresh_token)
  }

  function setUserInfo(user: UserInfo) {
    userInfo.value = user
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }

  async function login(username: string, password: string) {
    const tokenData = await authApi.login({ username, password })
    setToken(tokenData)
    const user = await authApi.getMe()
    setUserInfo(user)
    return user
  }

  async function fetchUserInfo() {
    if (!token.value) return null
    try {
      const user = await authApi.getMe()
      setUserInfo(user)
      return user
    } catch (e) {
      logout()
      return null
    }
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  // ✅ 修复后的权限检查（基于user_type）
  function hasPermission(permission: string): boolean {
    if (!userInfo.value) return false

    // 管理员拥有所有权限
    if (userInfo.value.user_type === 'admin') return true

    // 根据用户类型检查权限（与后端保持一致）
    const userType = userInfo.value.user_type

    // 定义权限映射（与后端 permissions.py 保持一致）
    const USER_PERMISSIONS = [
      'share:view', 'share:create', 'share:delete_own', 'share:save',
      'user:view_own', 'user:update_own', 'stats:view_own'
    ]

    const VIP_PERMISSIONS = [
      ...USER_PERMISSIONS,
      'share:priority', 'share:batch_create', 'share:export',
      'share:reparse', 'share:audit_own',  // ✅ 新增VIP权限
      'stats:view_advanced', 'api:rate_limit_high', 'feature:ad_free'
    ]

    if (userType === 'vip') {
      return VIP_PERMISSIONS.includes(permission)
    }

    if (userType === 'user') {
      return USER_PERMISSIONS.includes(permission)
    }

    return false
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    isAdmin,
    isVip,  // ✅ 导出isVip
    userType,  // ✅ 导出userType
    username,
    nickname,
    setToken,
    setUserInfo,
    login,
    fetchUserInfo,
    logout,
    hasPermission
  }
})

