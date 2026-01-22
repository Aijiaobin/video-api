<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
        </div>
      </template>

      <!-- 搜索表单 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchParams.keyword" placeholder="用户名/昵称" clearable @keyup.enter="loadData" />
        </el-form-item>
        <el-form-item label="用户类型">
          <el-select v-model="searchParams.user_type" placeholder="全部" clearable>
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
            <el-option label="VIP用户" value="vip" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchParams.is_active" placeholder="全部" clearable>
            <el-option label="正常" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 用户表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="user_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getUserTypeTag(row.user_type)">{{ getUserTypeName(row.user_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="share_count" label="分享数" width="80" />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="row.is_active" size="small" type="warning" @click="handleDisable(row)">禁用</el-button>
            <el-button v-else size="small" type="success" @click="handleEnable(row)">启用</el-button>
            <el-button size="small" type="danger" @click="handleResetPassword(row)">重置密码</el-button>
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

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="500px">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="editForm.nickname" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="用户类型" prop="user_type">
          <el-select v-model="editForm.user_type">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
            <el-option label="VIP用户" value="vip" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { userApi, type UserInfo } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<UserInfo[]>([])
const editDialogVisible = ref(false)
const editFormRef = ref<FormInstance>()

const searchParams = reactive({ keyword: '', user_type: '', is_active: undefined as boolean | undefined })
const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const editForm = reactive({ id: 0, username: '', nickname: '', email: '', user_type: '' })

const editRules: FormRules = {
  nickname: [{ max: 50, message: '昵称不能超过50个字符', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }]
}

function getUserTypeName(type: string) {
  const map: Record<string, string> = { admin: '管理员', user: '普通用户', vip: 'VIP用户' }
  return map[type] || type
}

function getUserTypeTag(type: string) {
  const map: Record<string, string> = { admin: 'danger', user: '', vip: 'warning' }
  return map[type] || ''
}

function formatDate(date: string) {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : ''
}

async function loadData() {
  loading.value = true
  try {
    const res = await userApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      ...searchParams
    })
    tableData.value = res.items
    pagination.total = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchParams.keyword = ''
  searchParams.user_type = ''
  searchParams.is_active = undefined
  pagination.page = 1
  loadData()
}

function handleEdit(row: UserInfo) {
  Object.assign(editForm, { id: row.id, username: row.username, nickname: row.nickname, email: row.email, user_type: row.user_type })
  editDialogVisible.value = true
}

async function handleSaveEdit() {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      await userApi.update(editForm.id, { nickname: editForm.nickname, email: editForm.email, user_type: editForm.user_type })
      ElMessage.success('保存成功')
      editDialogVisible.value = false
      loadData()
    } catch (e: any) {
      ElMessage.error(e.response?.data?.detail || '保存失败')
    }
  })
}

async function handleDisable(row: UserInfo) {
  await ElMessageBox.confirm(`确定要禁用用户 "${row.username}" 吗？`, '提示', { type: 'warning' })
  try {
    await userApi.disable(row.id)
    ElMessage.success('已禁用')
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleEnable(row: UserInfo) {
  try {
    await userApi.enable(row.id)
    ElMessage.success('已启用')
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleResetPassword(row: UserInfo) {
  const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
    inputPattern: /^.{6,}$/,
    inputErrorMessage: '密码长度不能少于6位'
  })
  try {
    await userApi.resetPassword(row.id, value)
    ElMessage.success('密码已重置')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.users-page { .search-form { margin-bottom: 20px; } }
</style>

