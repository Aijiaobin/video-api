<template>
  <div class="announcements-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>公告管理</span>
          <el-button type="primary" @click="handleCreate">新建公告</el-button>
        </div>
      </template>

      <!-- 搜索表单 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="类型">
          <el-select v-model="searchParams.type" placeholder="全部" clearable>
            <el-option label="通知" value="notice" />
            <el-option label="更新" value="update" />
            <el-option label="警告" value="warning" />
            <el-option label="活动" value="event" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchParams.is_active" placeholder="全部" clearable>
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 公告表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.type)">{{ getTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="position" label="位置" width="100">
          <template #default="{ row }">{{ getPositionName(row.position) }}</template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
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
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑公告' : '新建公告'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="公告标题" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="5" placeholder="公告内容（支持Markdown）" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type">
            <el-option label="通知" value="notice" />
            <el-option label="更新" value="update" />
            <el-option label="警告" value="warning" />
            <el-option label="活动" value="event" />
          </el-select>
        </el-form-item>
        <el-form-item label="显示位置" prop="position">
          <el-select v-model="form.position">
            <el-option label="全部" value="all" />
            <el-option label="首页" value="home" />
            <el-option label="分享页" value="share" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_at" type="datetime" placeholder="选择开始时间" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.end_at" type="datetime" placeholder="选择结束时间" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { announcementApi, type Announcement } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<Announcement[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()

const searchParams = reactive({ type: '', is_active: undefined as boolean | undefined })
const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const form = reactive({
  id: 0, title: '', content: '', type: 'notice', position: 'all',
  priority: 0, is_active: true, start_at: '', end_at: ''
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

function getTypeName(type: string) {
  const map: Record<string, string> = { notice: '通知', update: '更新', warning: '警告', event: '活动' }
  return map[type] || type
}

function getTypeTag(type: string) {
  const map: Record<string, string> = { notice: '', update: 'success', warning: 'warning', event: 'danger' }
  return map[type] || ''
}

function getPositionName(pos: string) {
  const map: Record<string, string> = { all: '全部', home: '首页', share: '分享页' }
  return map[pos] || pos
}

function formatDate(date: string) { return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '' }

async function loadData() {
  loading.value = true
  try {
    const res = await announcementApi.list({ page: pagination.page, page_size: pagination.page_size, ...searchParams })
    tableData.value = res.items
    pagination.total = res.total
  } catch (e) { console.error(e) } finally { loading.value = false }
}

function resetSearch() {
  searchParams.type = ''; searchParams.is_active = undefined
  pagination.page = 1; loadData()
}

function handleCreate() {
  isEdit.value = false
  Object.assign(form, { id: 0, title: '', content: '', type: 'notice', position: 'all', priority: 0, is_active: true, start_at: '', end_at: '' })
  dialogVisible.value = true
}

function handleEdit(row: Announcement) {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) { await announcementApi.update(form.id, form) }
      else { await announcementApi.create(form) }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadData()
    } catch (e: any) { ElMessage.error(e.response?.data?.detail || '保存失败') }
  })
}

async function handleDelete(row: Announcement) {
  await ElMessageBox.confirm(`确定要删除公告 "${row.title}" 吗？`, '提示', { type: 'warning' })
  try { await announcementApi.delete(row.id); ElMessage.success('已删除'); loadData() } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.announcements-page { .search-form { margin-bottom: 20px; } }
</style>

