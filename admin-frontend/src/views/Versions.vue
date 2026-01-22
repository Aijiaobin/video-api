<template>
  <div class="versions-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>版本管理</span>
          <el-button type="primary" @click="handleCreate">发布新版本</el-button>
        </div>
      </template>

      <!-- 版本表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="version_code" label="版本号" width="100" />
        <el-table-column prop="version_name" label="版本名称" width="120" />
        <el-table-column prop="update_title" label="更新标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="is_force_update" label="强制更新" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_force_update ? 'danger' : 'info'">{{ row.is_force_update ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_published" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_published ? 'success' : 'warning'">{{ row.is_published ? '已发布' : '未发布' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="download_count" label="下载量" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="!row.is_published" size="small" type="success" @click="handlePublish(row)">发布</el-button>
            <el-button v-else size="small" type="warning" @click="handleUnpublish(row)">取消发布</el-button>
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑版本' : '发布新版本'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="版本号" prop="version_code">
          <el-input-number v-model="form.version_code" :min="1" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="版本名称" prop="version_name">
          <el-input v-model="form.version_name" placeholder="如 1.0.0" />
        </el-form-item>
        <el-form-item label="更新标题" prop="update_title">
          <el-input v-model="form.update_title" placeholder="更新标题" />
        </el-form-item>
        <el-form-item label="更新说明" prop="update_content">
          <el-input v-model="form.update_content" type="textarea" :rows="4" placeholder="更新说明（支持Markdown）" />
        </el-form-item>
        <el-form-item label="下载地址" prop="download_url">
          <el-input v-model="form.download_url" placeholder="APK下载地址" />
        </el-form-item>
        <el-form-item label="文件大小">
          <el-input-number v-model="form.file_size" :min="0" /> <span style="margin-left: 8px;">字节</span>
        </el-form-item>
        <el-form-item label="文件MD5">
          <el-input v-model="form.file_md5" placeholder="文件MD5校验值" />
        </el-form-item>
        <el-form-item label="强制更新">
          <el-switch v-model="form.is_force_update" />
        </el-form-item>
        <el-form-item label="最低版本">
          <el-input-number v-model="form.min_version_code" :min="0" placeholder="低于此版本强制更新" />
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
import { versionApi, type AppVersion } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<AppVersion[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()

const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const form = reactive({
  id: 0, version_code: 1, version_name: '', update_title: '', update_content: '',
  download_url: '', file_size: 0, file_md5: '', is_force_update: false, min_version_code: 0
})

const rules: FormRules = {
  version_code: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  version_name: [{ required: true, message: '请输入版本名称', trigger: 'blur' }],
  download_url: [{ required: true, message: '请输入下载地址', trigger: 'blur' }]
}

function formatDate(date: string) {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : ''
}

async function loadData() {
  loading.value = true
  try {
    const res = await versionApi.list({ page: pagination.page, page_size: pagination.page_size })
    tableData.value = res.items
    pagination.total = res.total
  } catch (e) { console.error(e) } finally { loading.value = false }
}

function handleCreate() {
  isEdit.value = false
  Object.assign(form, { id: 0, version_code: 1, version_name: '', update_title: '', update_content: '', download_url: '', file_size: 0, file_md5: '', is_force_update: false, min_version_code: 0 })
  dialogVisible.value = true
}

function handleEdit(row: AppVersion) {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) {
        await versionApi.update(form.id, form)
      } else {
        await versionApi.create(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadData()
    } catch (e: any) { ElMessage.error(e.response?.data?.detail || '保存失败') }
  })
}

async function handlePublish(row: AppVersion) {
  await ElMessageBox.confirm(`确定要发布版本 "${row.version_name}" 吗？`, '提示', { type: 'warning' })
  try {
    await versionApi.publish(row.id)
    ElMessage.success('已发布')
    loadData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

async function handleUnpublish(row: AppVersion) {
  await ElMessageBox.confirm(`确定要取消发布版本 "${row.version_name}" 吗？`, '提示', { type: 'warning' })
  try {
    await versionApi.unpublish(row.id)
    ElMessage.success('已取消发布')
    loadData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

async function handleDelete(row: AppVersion) {
  await ElMessageBox.confirm(`确定要删除版本 "${row.version_name}" 吗？`, '提示', { type: 'warning' })
  try {
    await versionApi.delete(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

onMounted(() => loadData())
</script>

