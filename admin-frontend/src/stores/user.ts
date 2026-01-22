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

  function hasPermission(permission: string): boolean {
    if (!userInfo.value) return false
    if (userInfo.value.user_type === 'admin') return true
    return userInfo.value.roles?.some(role => 
      role.name === 'admin' || (role as any).permissions?.some((p: any) => p.name === permission)
    ) || false
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    isAdmin,
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

