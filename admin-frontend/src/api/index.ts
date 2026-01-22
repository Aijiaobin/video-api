import { http } from '@/utils/request'

// ========== 认证相关 ==========
export interface LoginParams {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: number
  username: string
  nickname: string
  email: string
  avatar_url: string
  user_type: string
  is_active: boolean
  share_count: number
  created_at: string
  roles: Array<{ id: number; name: string; display_name: string }>
}

export const authApi = {
  login: (data: LoginParams) => http.post<TokenResponse>('/auth/login', data),
  logout: () => http.post('/auth/logout'),
  getMe: () => http.get<UserInfo>('/auth/me'),
  refreshToken: (refreshToken: string) => http.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),
  changePassword: (data: { old_password: string; new_password: string }) => http.post('/auth/change-password', data)
}

// ========== 用户管理 ==========
export interface UserListParams {
  page?: number
  page_size?: number
  keyword?: string
  user_type?: string
  is_active?: boolean
}

export interface UserListResponse {
  total: number
  page: number
  page_size: number
  items: UserInfo[]
}

export const userApi = {
  list: (params: UserListParams) => http.get<UserListResponse>('/admin/users', { params }),
  get: (id: number) => http.get<UserInfo>(`/admin/users/${id}`),
  update: (id: number, data: Partial<UserInfo>) => http.put(`/admin/users/${id}`, data),
  disable: (id: number) => http.post(`/admin/users/${id}/disable`),
  enable: (id: number) => http.post(`/admin/users/${id}/enable`),
  resetPassword: (id: number, password: string) => http.post(`/admin/users/${id}/reset-password`, { new_password: password }),
  assignRoles: (id: number, roleIds: number[]) => http.post(`/admin/users/${id}/roles`, { role_ids: roleIds }),
  delete: (id: number) => http.delete(`/admin/users/${id}`)
}

// ========== 版本管理 ==========
export interface AppVersion {
  id: number
  version_code: number
  version_name: string
  update_title: string
  update_content: string
  download_url: string
  file_size: number
  file_md5: string
  is_force_update: boolean
  min_version_code: number
  is_published: boolean
  published_at: string
  download_count: number
  created_at: string
}

export interface VersionListResponse {
  total: number
  page: number
  page_size: number
  items: AppVersion[]
}

export const versionApi = {
  list: (params: { page?: number; page_size?: number }) => http.get<VersionListResponse>('/admin/versions', { params }),
  get: (id: number) => http.get<AppVersion>(`/admin/versions/${id}`),
  create: (data: Partial<AppVersion>) => http.post<AppVersion>('/admin/versions', data),
  update: (id: number, data: Partial<AppVersion>) => http.put<AppVersion>(`/admin/versions/${id}`, data),
  publish: (id: number) => http.post<AppVersion>(`/admin/versions/${id}/publish`),
  unpublish: (id: number) => http.post<AppVersion>(`/admin/versions/${id}/unpublish`),
  delete: (id: number) => http.delete(`/admin/versions/${id}`)
}

// ========== 分享管理 ==========
export interface ShareItem {
  id: number
  drive_type: string
  share_url: string
  share_code: string
  password: string
  raw_title: string
  clean_title: string
  share_type: string
  poster_url: string
  file_count: number
  view_count: number
  save_count: number
  status: string
  created_at: string
  submitter?: {
    id: number
    username: string
    nickname: string
  }
}

export interface ShareListParams {
  page?: number
  page_size?: number
  status?: string
  drive_type?: string
  keyword?: string
  submitter_id?: number
}

export interface ShareListResponse {
  total: number
  page: number
  page_size: number
  items: ShareItem[]
}

export interface BatchShareItem {
  drive_type: string
  share_url: string
  password?: string
}

export interface BatchImportResponse {
  total: number
  success: number
  failed: number
  duplicates: number
  results: Array<{ share_url: string; status: string; message: string; share_id?: number }>
}

export const shareApi = {
  list: (params: ShareListParams) => http.get<ShareListResponse>('/admin/shares', { params }),
  audit: (id: number, data: { status: string; reason?: string }) => http.post(`/admin/shares/${id}/audit`, data),
  batchAudit: (ids: number[], status: string, reason?: string) =>
    http.post('/admin/shares/batch-audit', null, { params: { share_ids: ids, status, reason } }),
  delete: (id: number) => http.delete(`/admin/shares/${id}`),
  batchImport: (shares: BatchShareItem[]) => http.post<BatchImportResponse>('/user/shares/batch', { shares }),
  reparse: (id: number) => http.post(`/admin/shares/${id}/reparse`),
  reparseAll: () => http.post('/admin/shares/reparse-all'),
  reparseUnparsed: (threads: number = 5) => http.post('/admin/shares/reparse-unparsed', null, { params: { threads } })
}

// ========== 公告管理 ==========
export interface Announcement {
  id: number
  title: string
  content: string
  type: string
  position: string
  priority: number
  is_active: boolean
  start_at: string
  end_at: string
  created_at: string
}

export interface AnnouncementListResponse {
  total: number
  page: number
  page_size: number
  items: Announcement[]
}

export const announcementApi = {
  list: (params: { page?: number; page_size?: number; type?: string; is_active?: boolean }) => 
    http.get<AnnouncementListResponse>('/admin/announcements', { params }),
  get: (id: number) => http.get<Announcement>(`/admin/announcements/${id}`),
  create: (data: Partial<Announcement>) => http.post<Announcement>('/admin/announcements', data),
  update: (id: number, data: Partial<Announcement>) => http.put<Announcement>(`/admin/announcements/${id}`, data),
  delete: (id: number) => http.delete(`/admin/announcements/${id}`)
}

// ========== 系统配置 ==========
export interface SystemConfig {
  id: number
  config_key: string
  config_value: string
  config_group: string
  description: string
  is_sensitive: boolean
  created_at: string
}

export const configApi = {
  list: (group?: string) => http.get<{ items: SystemConfig[] }>('/admin/configs', { params: { group } }),
  create: (data: Partial<SystemConfig>) => http.post<SystemConfig>('/admin/configs', data),
  update: (key: string, data: { config_value?: string; description?: string }) => 
    http.put<SystemConfig>(`/admin/configs/${key}`, data),
  delete: (key: string) => http.delete(`/admin/configs/${key}`)
}

// ========== 统计 ==========
export interface OverviewStats {
  total_users: number
  total_shares: number
  total_views: number
  total_saves: number
  today_users: number
  today_shares: number
  active_users: number
  pending_shares: number
}

export interface TrendItem {
  date: string
  count: number
}

export interface TrendStats {
  users: TrendItem[]
  shares: TrendItem[]
  views: TrendItem[]
}

export interface RankItem {
  id: number
  title: string
  poster_url: string
  count: number
  drive_type: string
}

export interface RankStats {
  hot_shares: RankItem[]
  top_saves: RankItem[]
  top_sharers: Array<{ id: number; username: string; nickname: string; share_count: number }>
}

export const statsApi = {
  overview: () => http.get<OverviewStats>('/admin/stats/overview'),
  trends: (days?: number) => http.get<TrendStats>('/admin/stats/trends', { params: { days } }),
  rankings: (limit?: number) => http.get<RankStats>('/admin/stats/rankings', { params: { limit } }),
  driveTypes: () => http.get<Array<{ drive_type: string; count: number; percentage: number }>>('/admin/stats/drive-types'),
  shareTypes: () => http.get<Array<{ share_type: string; count: number; percentage: number }>>('/admin/stats/share-types')
}

