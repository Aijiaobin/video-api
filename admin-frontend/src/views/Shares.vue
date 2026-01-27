<template>
  <div class="shares-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分享管理</span>
          <div>
            <el-button type="success" @click="handleReparseUnparsed" :loading="reparseUnparsedLoading">解析未解析的</el-button>
            <el-button type="warning" @click="handleReparseAll" :loading="reparseLoading">重新解析全部</el-button>
            <el-button type="primary" @click="showImportDialog">批量导入</el-button>
          </div>
        </div>
      </template>

      <!-- 搜索表单 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchParams.keyword" placeholder="标题" clearable @keyup.enter="loadData" />
        </el-form-item>
        <el-form-item label="网盘类型">
          <el-select v-model="searchParams.drive_type" placeholder="全部" clearable>
            <el-option label="天翼云盘" value="tianyi" />
            <el-option label="阿里云盘" value="aliyun" />
            <el-option label="夸克网盘" value="quark" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchParams.status" placeholder="全部" clearable>
            <el-option label="已通过" value="active" />
            <el-option label="待审核" value="pending" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已删除" value="deleted" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 批量操作 -->
      <div class="batch-actions" v-if="selectedIds.length > 0">
        <el-button type="success" size="small" @click="handleBatchAudit('approved')">批量通过</el-button>
        <el-button type="danger" size="small" @click="handleBatchAudit('rejected')">批量拒绝</el-button>
        <span class="selected-count">已选择 {{ selectedIds.length }} 项</span>
      </div>

      <!-- 分享表格 -->
      <el-table :data="tableData" v-loading="loading" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="封面" width="80">
          <template #default="{ row }">
            <el-image v-if="row.poster_url" :src="row.poster_url" fit="cover" style="width: 50px; height: 70px;" />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="clean_title" label="标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.clean_title || row.raw_title || '-' }}</template>
        </el-table-column>
        <el-table-column prop="drive_type" label="网盘" width="100">
          <template #default="{ row }">{{ getDriveTypeName(row.drive_type) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusName(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="view_count" label="浏览" width="80" />
        <el-table-column prop="save_count" label="转存" width="80" />
        <el-table-column label="提交者" width="120">
          <template #default="{ row }">{{ row.submitter?.nickname || row.submitter?.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="success" @click="handleAudit(row, 'approved')">通过</el-button>
              <el-button size="small" type="danger" @click="handleAudit(row, 'rejected')">拒绝</el-button>
            </template>
            <el-button size="small" type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="handleReparse(row)">解析</el-button>
            <el-button size="small" @click="handleViewDetail(row)">详情</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="分享详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="ID">{{ currentShare?.id }}</el-descriptions-item>
        <el-descriptions-item label="网盘类型">{{ getDriveTypeName(currentShare?.drive_type) }}</el-descriptions-item>
        <el-descriptions-item label="原始标题" :span="2">{{ currentShare?.raw_title }}</el-descriptions-item>
        <el-descriptions-item label="清洗标题" :span="2">{{ currentShare?.clean_title }}</el-descriptions-item>
        <el-descriptions-item label="分享链接" :span="2">
          <el-link :href="currentShare?.share_url" target="_blank" type="primary">{{ currentShare?.share_url }}</el-link>
        </el-descriptions-item>
        <el-descriptions-item label="提取码">{{ currentShare?.password || '无' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentShare?.status)">{{ getStatusName(currentShare?.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="浏览量">{{ currentShare?.view_count }}</el-descriptions-item>
        <el-descriptions-item label="转存量">{{ currentShare?.save_count }}</el-descriptions-item>
        <el-descriptions-item label="文件数">{{ currentShare?.file_count }}</el-descriptions-item>
        <el-descriptions-item label="提交者">{{ currentShare?.submitter?.nickname || currentShare?.submitter?.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ formatDate(currentShare?.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 编辑标题对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑分享标题" width="600px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="原始标题">
          <el-input v-model="editForm.raw_title" disabled />
        </el-form-item>
        <el-form-item label="自动清洗标题">
          <el-input v-model="editForm.clean_title" disabled />
        </el-form-item>
        <el-form-item label="手动修正标题">
          <el-input v-model="editForm.manual_title" placeholder="留空则使用自动清洗的标题" clearable />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            手动修正的标题优先级高于自动清洗的标题
          </div>
        </el-form-item>
        <el-form-item label="媒体类型">
          <el-select v-model="editForm.share_type" placeholder="选择媒体类型" style="width: 100%;">
            <el-option label="剧集 (tv)" value="tv" />
            <el-option label="电影 (movie)" value="movie" />
            <el-option label="电影合集" value="movie_collection" />
          </el-select>
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            决定使用 TMDB 的 movie 还是 tv 接口搜索
          </div>
        </el-form-item>
        <el-form-item label="提取的TMDB ID">
          <el-input v-model="editForm.extracted_tmdb_id" disabled />
        </el-form-item>
        <el-form-item label="手动指定TMDB ID">
          <el-input-number v-model="editForm.manual_tmdb_id" :min="0" placeholder="留空则使用提取的ID" style="width: 100%;" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            手动指定的TMDB ID优先级最高，可用于修正错误的刮削结果
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleSaveEdit">保存</el-button>
        <el-button type="success" :loading="rescrapeLoading" @click="handleRescrapeAfterEdit">保存并重新刮削</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="批量导入分享链接" width="700px">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px;">
        <template #title>
          <div>支持格式（每行一个）：</div>
          <div style="font-size: 12px; margin-top: 4px;">
            1. 纯链接：https://cloud.189.cn/t/xxx<br>
            2. 链接+提取码：https://cloud.189.cn/t/xxx 提取码: abc123<br>
            3. 链接 密码：https://cloud.189.cn/t/xxx abc123
          </div>
        </template>
      </el-alert>

      <el-form label-width="80px">
        <el-form-item label="网盘类型">
          <el-select v-model="importForm.drive_type" placeholder="选择网盘类型">
            <el-option label="天翼云盘" value="tianyi" />
            <el-option label="阿里云盘" value="aliyun" />
            <el-option label="夸克网盘" value="quark" />
          </el-select>
        </el-form-item>
        <el-form-item label="分享链接">
          <el-input
            v-model="importForm.text"
            type="textarea"
            :rows="10"
            placeholder="请粘贴分享链接，每行一个..."
          />
        </el-form-item>
      </el-form>

      <!-- 导入结果 -->
      <div v-if="importResult" class="import-result">
        <el-divider>导入结果</el-divider>
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="总数">{{ importResult.total }}</el-descriptions-item>
          <el-descriptions-item label="成功"><span class="text-success">{{ importResult.success }}</span></el-descriptions-item>
          <el-descriptions-item label="重复"><span class="text-warning">{{ importResult.duplicates }}</span></el-descriptions-item>
          <el-descriptions-item label="失败"><span class="text-danger">{{ importResult.failed }}</span></el-descriptions-item>
        </el-descriptions>
        <div class="result-list" v-if="importResult.results.length > 0">
          <div v-for="(r, i) in importResult.results" :key="i" class="result-item" :class="r.status">
            <el-icon v-if="r.status === 'success'"><CircleCheck /></el-icon>
            <el-icon v-else-if="r.status === 'duplicate'"><Warning /></el-icon>
            <el-icon v-else><CircleClose /></el-icon>
            <span class="url">{{ r.share_url.substring(0, 50) }}{{ r.share_url.length > 50 ? '...' : '' }}</span>
            <span class="msg">{{ r.message }}</span>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="importLoading" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Warning, CircleClose } from '@element-plus/icons-vue'
import { shareApi, type ShareItem, type BatchImportResponse } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<ShareItem[]>([])
const selectedIds = ref<number[]>([])
const detailDialogVisible = ref(false)
const currentShare = ref<ShareItem | null>(null)
const reparseLoading = ref(false)

// 编辑相关
const editDialogVisible = ref(false)
const editLoading = ref(false)
const rescrapeLoading = ref(false)
const editForm = reactive({
  id: 0,
  raw_title: '',
  clean_title: '',
  manual_title: '',
  share_type: '',
  extracted_tmdb_id: null as number | null,
  manual_tmdb_id: null as number | null
})

// 批量导入相关
const importDialogVisible = ref(false)
const importLoading = ref(false)
const importResult = ref<BatchImportResponse | null>(null)
const importForm = reactive({ drive_type: 'tianyi', text: '' })

const searchParams = reactive({ keyword: '', drive_type: '', status: '' })
const pagination = reactive({ page: 1, page_size: 20, total: 0 })

function getDriveTypeName(type: string) {
  const map: Record<string, string> = { tianyi: '天翼云盘', aliyun: '阿里云盘', quark: '夸克网盘' }
  return map[type] || type
}

function getStatusName(status: string) {
  const map: Record<string, string> = { active: '已通过', pending: '待审核', rejected: '已拒绝', deleted: '已删除', expired: '已失效' }
  return map[status] || status
}

function getStatusType(status: string) {
  const map: Record<string, string> = { active: 'success', pending: 'warning', rejected: 'danger', deleted: 'info', expired: 'info' }
  return map[status] || ''
}

function getShareTypeName(type: string) {
  const map: Record<string, string> = { tv: '剧集 (tv)', movie: '电影 (movie)', movie_collection: '电影合集' }
  return map[type] || type || '未知'
}

function formatDate(date: string) { return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '' }

async function loadData() {
  loading.value = true
  try {
    const res = await shareApi.list({ page: pagination.page, page_size: pagination.page_size, ...searchParams })
    tableData.value = res.items
    pagination.total = res.total
  } catch (e) { console.error(e) } finally { loading.value = false }
}

function resetSearch() {
  searchParams.keyword = ''; searchParams.drive_type = ''; searchParams.status = ''
  pagination.page = 1; loadData()
}

function handleSelectionChange(selection: ShareItem[]) { selectedIds.value = selection.map(s => s.id) }

function handleViewDetail(row: ShareItem) { currentShare.value = row; detailDialogVisible.value = true }

async function handleAudit(row: ShareItem, status: string) {
  let reason = ''
  if (status === 'rejected') {
    const { value } = await ElMessageBox.prompt('请输入拒绝原因', '拒绝', { inputPlaceholder: '拒绝原因（可选）' }).catch(() => ({ value: '' }))
    reason = value
  }
  try {
    await shareApi.audit(row.id, { status, reason })
    ElMessage.success(status === 'approved' ? '已通过' : '已拒绝')
    loadData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

async function handleBatchAudit(status: string) {
  let reason = ''
  if (status === 'rejected') {
    const { value } = await ElMessageBox.prompt('请输入拒绝原因', '批量拒绝', { inputPlaceholder: '拒绝原因（可选）' }).catch(() => ({ value: '' }))
    reason = value
  }
  try {
    await shareApi.batchAudit(selectedIds.value, status, reason)
    ElMessage.success(`已${status === 'approved' ? '通过' : '拒绝'} ${selectedIds.value.length} 个分享`)
    selectedIds.value = []; loadData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

async function handleDelete(row: ShareItem) {
  await ElMessageBox.confirm(`确定要删除该分享吗？`, '提示', { type: 'warning' })
  try { await shareApi.delete(row.id); ElMessage.success('已删除'); loadData() } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

// 重新解析功能
async function handleReparse(row: ShareItem) {
  try {
    await shareApi.reparse(row.id)
    ElMessage.success('已提交重新解析任务')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

// 编辑功能
function handleEdit(row: ShareItem) {
  editForm.id = row.id
  editForm.raw_title = row.raw_title || ''
  editForm.clean_title = row.clean_title || ''
  editForm.manual_title = row.manual_title || ''
  editForm.share_type = row.share_type || 'tv'
  editForm.extracted_tmdb_id = row.extracted_tmdb_id || null
  editForm.manual_tmdb_id = row.manual_tmdb_id || null
  editDialogVisible.value = true
}

async function handleSaveEdit() {
  editLoading.value = true
  try {
    await shareApi.editTitle(editForm.id, {
      manual_title: editForm.manual_title || null,
      manual_tmdb_id: editForm.manual_tmdb_id || null,
      share_type: editForm.share_type || null
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    editLoading.value = false
  }
}

async function handleRescrapeAfterEdit() {
  rescrapeLoading.value = true
  try {
    // 先保存编辑
    await shareApi.editTitle(editForm.id, {
      manual_title: editForm.manual_title || null,
      manual_tmdb_id: editForm.manual_tmdb_id || null,
      share_type: editForm.share_type || null
    })
    // 再重新刮削
    await shareApi.rescrape(editForm.id, { force: true })
    ElMessage.success('保存成功，已提交重新刮削任务')
    editDialogVisible.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    rescrapeLoading.value = false
  }
}

async function handleReparseAll() {
  await ElMessageBox.confirm('确定要重新解析所有分享吗？这可能需要一些时间。', '提示', { type: 'warning' })
  reparseLoading.value = true
  try {
    const res = await shareApi.reparseAll()
    ElMessage.success(res.message || '已提交重新解析任务')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    reparseLoading.value = false
  }
}

const reparseUnparsedLoading = ref(false)

async function handleReparseUnparsed() {
  await ElMessageBox.confirm('确定要解析所有未解析的分享吗？将使用5线程并发解析。', '提示', { type: 'info' })
  reparseUnparsedLoading.value = true
  try {
    const res = await shareApi.reparseUnparsed(5)
    ElMessage.success(res.message || '已提交解析任务')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    reparseUnparsedLoading.value = false
  }
}

// 批量导入功能
function showImportDialog() {
  importForm.text = ''
  importResult.value = null
  importDialogVisible.value = true
}

function parseShareLines(text: string, driveType: string) {
  const lines = text.split('\n').filter(line => line.trim())
  const shares: Array<{ drive_type: string; share_url: string; password?: string }> = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    // 尝试匹配各种格式
    // 格式1: 链接 提取码: xxx 或 链接 密码: xxx
    let match = trimmed.match(/^(https?:\/\/[^\s]+)\s+(?:提取码|密码)[：:]\s*(\S+)$/i)
    if (match) {
      shares.push({ drive_type: driveType, share_url: match[1], password: match[2] })
      continue
    }

    // 格式2: 链接 xxx (空格分隔)
    match = trimmed.match(/^(https?:\/\/[^\s]+)\s+(\S+)$/)
    if (match) {
      shares.push({ drive_type: driveType, share_url: match[1], password: match[2] })
      continue
    }

    // 格式3: 纯链接
    match = trimmed.match(/^(https?:\/\/[^\s]+)$/)
    if (match) {
      shares.push({ drive_type: driveType, share_url: match[1] })
      continue
    }
  }

  return shares
}

async function handleImport() {
  if (!importForm.drive_type) {
    ElMessage.warning('请选择网盘类型')
    return
  }
  if (!importForm.text.trim()) {
    ElMessage.warning('请输入分享链接')
    return
  }

  const shares = parseShareLines(importForm.text, importForm.drive_type)
  if (shares.length === 0) {
    ElMessage.warning('未识别到有效的分享链接')
    return
  }

  if (shares.length > 1000) {  // ✅ 改为1000
    ElMessage.warning('单次最多导入1000个链接')
    return
  }

  importLoading.value = true
  try {
    const res = await shareApi.batchImport(shares)
    importResult.value = res
    ElMessage.success(`导入完成：成功 ${res.success} 个，重复 ${res.duplicates} 个，失败 ${res.failed} 个`)
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importLoading.value = false
  }
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.shares-page {
  .search-form { margin-bottom: 20px; }
  .batch-actions {
    margin-bottom: 16px;
    .selected-count { margin-left: 16px; color: #909399; }
  }
}

.import-result {
  .text-success { color: #67c23a; font-weight: bold; }
  .text-warning { color: #e6a23c; font-weight: bold; }
  .text-danger { color: #f56c6c; font-weight: bold; }

  .result-list {
    max-height: 200px;
    overflow-y: auto;
    margin-top: 12px;
    border: 1px solid #ebeef5;
    border-radius: 4px;

    .result-item {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      border-bottom: 1px solid #ebeef5;
      font-size: 13px;

      &:last-child { border-bottom: none; }

      .el-icon { margin-right: 8px; font-size: 16px; }
      .url { flex: 1; color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .msg { margin-left: 12px; color: #909399; }

      &.success { .el-icon { color: #67c23a; } }
      &.duplicate { .el-icon { color: #e6a23c; } }
      &.failed { .el-icon { color: #f56c6c; } }
    }
  }
}
</style>

