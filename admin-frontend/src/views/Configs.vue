<template>
  <div class="configs-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统配置</span>
          <el-button type="primary" @click="handleCreate">新增配置</el-button>
        </div>
      </template>

      <!-- 分组筛选 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="配置分组">
          <el-select v-model="currentGroup" placeholder="全部" clearable @change="loadData">
            <el-option label="全部" value="" />
            <el-option label="TMDB配置" value="tmdb" />
            <el-option label="网盘配置" value="drive" />
            <el-option label="系统配置" value="system" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 配置表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="config_key" label="配置键" width="200" />
        <el-table-column prop="config_value" label="配置值" min-width="250">
          <template #default="{ row }">
            <span v-if="row.is_sensitive">******</span>
            <span v-else>{{ row.config_value || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="config_group" label="分组" width="120">
          <template #default="{ row }">
            <el-tag>{{ getGroupName(row.config_group) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" width="200" show-overflow-tooltip />
        <el-table-column prop="is_sensitive" label="敏感" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_sensitive" type="danger">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 常用配置快捷设置 -->
    <el-card style="margin-top: 20px;">
      <template #header><span>快捷配置</span></template>
      <el-tabs>
        <el-tab-pane label="TMDB配置">
          <el-form label-width="120px" style="max-width: 500px;">
            <el-form-item label="API Key">
              <el-input v-model="quickConfig.tmdb_api_key" type="password" show-password placeholder="TMDB API Key" />
            </el-form-item>
            <el-form-item label="图片代理">
              <el-input v-model="quickConfig.tmdb_image_proxy" placeholder="图片代理地址" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveQuickConfig('tmdb')">保存TMDB配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="网盘配置">
          <el-form label-width="120px" style="max-width: 500px;">
            <el-form-item label="天翼Cookie">
              <el-input v-model="quickConfig.tianyi_cookie" type="textarea" :rows="2" placeholder="天翼云盘Cookie" />
            </el-form-item>
            <el-form-item label="阿里Token">
              <el-input v-model="quickConfig.aliyun_token" type="password" show-password placeholder="阿里云盘Token" />
            </el-form-item>
            <el-form-item label="夸克Cookie">
              <el-input v-model="quickConfig.quark_cookie" type="textarea" :rows="2" placeholder="夸克网盘Cookie" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveQuickConfig('drive')">保存网盘配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑配置' : '新增配置'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="配置键" prop="config_key">
          <el-input v-model="form.config_key" :disabled="isEdit" placeholder="如 tmdb_api_key" />
        </el-form-item>
        <el-form-item label="配置值" prop="config_value">
          <el-input v-model="form.config_value" type="textarea" :rows="3" placeholder="配置值" />
        </el-form-item>
        <el-form-item label="分组" prop="config_group">
          <el-select v-model="form.config_group" placeholder="选择分组">
            <el-option label="TMDB配置" value="tmdb" />
            <el-option label="网盘配置" value="drive" />
            <el-option label="系统配置" value="system" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="配置说明" />
        </el-form-item>
        <el-form-item label="敏感配置" v-if="!isEdit">
          <el-switch v-model="form.is_sensitive" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">敏感配置的值将被隐藏显示</span>
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
import { configApi, type SystemConfig } from '@/api'

const loading = ref(false)
const tableData = ref<SystemConfig[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const currentGroup = ref('')

const form = reactive({ config_key: '', config_value: '', config_group: '', description: '', is_sensitive: false })
const quickConfig = reactive({
  tmdb_api_key: '', tmdb_image_proxy: '',
  tianyi_cookie: '', aliyun_token: '', quark_cookie: ''
})

const rules: FormRules = {
  config_key: [{ required: true, message: '请输入配置键', trigger: 'blur' }]
}

function getGroupName(group: string) {
  const map: Record<string, string> = { tmdb: 'TMDB', drive: '网盘', system: '系统', other: '其他' }
  return map[group] || group || '未分组'
}

async function loadData() {
  loading.value = true
  try {
    const res = await configApi.list(currentGroup.value || undefined)
    tableData.value = res.items
  } catch (e) { console.error(e) } finally { loading.value = false }
}

function handleCreate() {
  isEdit.value = false
  Object.assign(form, { config_key: '', config_value: '', config_group: '', description: '', is_sensitive: false })
  dialogVisible.value = true
}

function handleEdit(row: SystemConfig) {
  isEdit.value = true
  Object.assign(form, { config_key: row.config_key, config_value: row.is_sensitive ? '' : row.config_value, config_group: row.config_group, description: row.description, is_sensitive: row.is_sensitive })
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) {
        await configApi.update(form.config_key, { config_value: form.config_value, description: form.description })
      } else {
        await configApi.create(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadData()
    } catch (e: any) { ElMessage.error(e.response?.data?.detail || '保存失败') }
  })
}

async function handleDelete(row: SystemConfig) {
  await ElMessageBox.confirm(`确定要删除配置 "${row.config_key}" 吗？`, '提示', { type: 'warning' })
  try { await configApi.delete(row.config_key); ElMessage.success('已删除'); loadData() } catch (e: any) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

async function saveQuickConfig(type: string) {
  try {
    if (type === 'tmdb') {
      if (quickConfig.tmdb_api_key) await saveOrUpdateConfig('tmdb_api_key', quickConfig.tmdb_api_key, 'tmdb', 'TMDB API Key', true)
      if (quickConfig.tmdb_image_proxy) await saveOrUpdateConfig('tmdb_image_proxy', quickConfig.tmdb_image_proxy, 'tmdb', 'TMDB图片代理地址', false)
    } else if (type === 'drive') {
      if (quickConfig.tianyi_cookie) await saveOrUpdateConfig('tianyi_cookie', quickConfig.tianyi_cookie, 'drive', '天翼云盘Cookie', true)
      if (quickConfig.aliyun_token) await saveOrUpdateConfig('aliyun_token', quickConfig.aliyun_token, 'drive', '阿里云盘Token', true)
      if (quickConfig.quark_cookie) await saveOrUpdateConfig('quark_cookie', quickConfig.quark_cookie, 'drive', '夸克网盘Cookie', true)
    }
    ElMessage.success('保存成功')
    loadData()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '保存失败') }
}

async function saveOrUpdateConfig(key: string, value: string, group: string, desc: string, sensitive: boolean) {
  const existing = tableData.value.find(c => c.config_key === key)
  if (existing) {
    await configApi.update(key, { config_value: value })
  } else {
    await configApi.create({ config_key: key, config_value: value, config_group: group, description: desc, is_sensitive: sensitive })
  }
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.configs-page { .search-form { margin-bottom: 20px; } }
</style>

