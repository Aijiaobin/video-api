<template>
  <div class="roles-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            创建角色
          </el-button>
        </div>
      </template>

      <!-- 角色列表 -->
      <el-table :data="roles" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="角色标识" width="150" />
        <el-table-column prop="display_name" label="显示名称" width="150" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="权限数量" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.permissions?.length || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="系统角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_system ? 'danger' : 'success'">
              {{ row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleViewPermissions(row)">
              查看权限
            </el-button>
            <el-button size="small" @click="handleEdit(row)" :disabled="row.is_system">
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
              :disabled="row.is_system"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑角色对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="角色标识" prop="name">
          <el-input v-model="form.name" placeholder="例如: editor" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="例如: 编辑员" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="3"
            placeholder="角色描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 权限管理对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      title="权限管理"
      width="800px"
    >
      <div v-if="currentRole">
        <h3>{{ currentRole.display_name }} ({{ currentRole.name }})</h3>
        <el-divider />
        
        <el-button 
          type="primary" 
          @click="showAssignPermissions = true"
          style="margin-bottom: 20px"
          :disabled="currentRole.is_system"
        >
          分配权限
        </el-button>

        <!-- 当前权限列表 -->
        <el-table :data="currentRole.permissions" style="width: 100%">
          <el-table-column prop="name" label="权限标识" width="200" />
          <el-table-column prop="display_name" label="显示名称" width="150" />
          <el-table-column prop="group" label="分组" width="120">
            <template #default="{ row }">
              <el-tag>{{ row.group }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" />
        </el-table>
      </div>
    </el-dialog>

    <!-- 分配权限对话框 -->
    <el-dialog
      v-model="showAssignPermissions"
      title="分配权限"
      width="800px"
    >
      <el-checkbox-group v-model="selectedPermissions">
        <div v-for="(perms, group) in groupedPermissions" :key="group" style="margin-bottom: 20px">
          <h4>{{ group }}</h4>
          <el-checkbox 
            v-for="perm in perms" 
            :key="perm.id" 
            :label="perm.id"
            style="display: block; margin: 10px 0"
          >
            <strong>{{ perm.display_name }}</strong> ({{ perm.name }})
            <br />
            <span style="color: #999; font-size: 12px">{{ perm.description }}</span>
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="showAssignPermissions = false">取消</el-button>
        <el-button type="primary" @click="handleAssignPermissions" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import axios from '../utils/request'

interface Permission {
  id: number
  name: string
  display_name: string
  description: string
  group: string
}

interface Role {
  id: number
  name: string
  display_name: string
  description: string
  is_system: boolean
  permissions: Permission[]
}

// 状态
const loading = ref(false)
const submitting = ref(false)
const roles = ref<Role[]>([])
const allPermissions = ref<Permission[]>([])
const groupedPermissions = ref<Record<string, Permission[]>>({})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('创建角色')
const permissionDialogVisible = ref(false)
const showAssignPermissions = ref(false)
const currentRole = ref<Role | null>(null)
const selectedPermissions = ref<number[]>([])

// 表单
const formRef = ref()
const form = reactive({
  name: '',
  display_name: '',
  description: ''
})

const rules = {
  name: [
    { required: true, message: '请输入角色标识', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  display_name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' }
  ]
}

// 加载角色列表
async function loadRoles() {
  loading.value = true
  try {
    const response = await axios.get('/admin/roles')
    roles.value = response.data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载角色列表失败')
  } finally {
    loading.value = false
  }
}

// 加载所有权限
async function loadPermissions() {
  try {
    const response = await axios.get('/admin/roles/permissions/grouped')
    console.log('Permissions response:', response.data)
    groupedPermissions.value = response.data

    // 展平为数组
    const allPerms: Permission[] = []
    for (const group in response.data) {
      if (Array.isArray(response.data[group])) {
        allPerms.push(...response.data[group])
      }
    }
    allPermissions.value = allPerms
    console.log('All permissions loaded:', allPerms.length)
  } catch (error: any) {
    console.error('Load permissions error:', error)
    ElMessage.error(error.response?.data?.detail || '加载权限列表失败')
  }
}

// 创建角色
function handleCreate() {
  dialogTitle.value = '创建角色'
  form.name = ''
  form.display_name = ''
  form.description = ''
  dialogVisible.value = true
}

// 编辑角色
function handleEdit(role: Role) {
  dialogTitle.value = '编辑角色'
  form.name = role.name
  form.display_name = role.display_name
  form.description = role.description
  currentRole.value = role
  dialogVisible.value = true
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return

    submitting.value = true
    try {
      if (dialogTitle.value === '创建角色') {
        await axios.post('/admin/roles', form)
        ElMessage.success('角色创建成功')
      } else {
        await axios.put(`/admin/roles/${currentRole.value?.id}`, form)
        ElMessage.success('角色更新成功')
      }
      dialogVisible.value = false
      loadRoles()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

// 删除角色
async function handleDelete(role: Role) {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色 "${role.display_name}" 吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await axios.delete(`/admin/roles/${role.id}`)
    ElMessage.success('角色已删除')
    loadRoles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 查看权限
async function handleViewPermissions(role: Role) {
  currentRole.value = role
  selectedPermissions.value = role.permissions.map(p => p.id)
  permissionDialogVisible.value = true
}

// 分配权限
async function handleAssignPermissions() {
  if (!currentRole.value) return

  submitting.value = true
  try {
    await axios.post(
      `/admin/roles/${currentRole.value.id}/permissions`,
      selectedPermissions.value
    )
    ElMessage.success('权限分配成功')
    showAssignPermissions.value = false
    loadRoles()

    // 更新当前角色的权限显示
    const updatedRole = await axios.get(`/admin/roles/${currentRole.value.id}`)
    currentRole.value = updatedRole.data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '权限分配失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadRoles()
  loadPermissions()
})
</script>

<style scoped>
.roles-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

