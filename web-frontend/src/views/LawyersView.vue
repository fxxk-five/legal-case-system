<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">管理员</p>
        <h2>律师管理</h2>
      </div>
      <div class="toolbar">
        <el-button @click="openInviteDialog">生成邀请链接</el-button>
        <el-button type="primary" @click="dialogVisible = true">新增律师</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="lawyers" stripe empty-text="暂无律师数据">
      <el-table-column prop="real_name" label="姓名" min-width="120" />
      <el-table-column prop="phone" label="手机号" min-width="150" />
      <el-table-column label="角色" min-width="120">
        <template #default="{ row }">
          {{ formatRole(row.role) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'warning'">
            {{ row.status === 1 ? '已启用' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="toggleStatus(row)">
            {{ row.status === 1 ? '停用账号' : '启用账号' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="section-heading pending-block">
      <div>
        <p class="header-label">审批</p>
        <h2>待审批律师</h2>
      </div>
    </div>

    <el-table v-loading="loading" :data="pendingUsers" stripe empty-text="暂无待审批律师">
      <el-table-column prop="real_name" label="姓名" min-width="120" />
      <el-table-column prop="phone" label="手机号" min-width="150" />
      <el-table-column label="角色" min-width="120">
        <template #default="{ row }">
          {{ formatRole(row.role) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="approve(row.id)">审批通过</el-button>
          <el-button link type="danger" @click="reject(row.id)">拒绝申请</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新增律师" width="520px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
          <div class="field-tip">请输入律师真实姓名，最多 100 个字符。</div>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
          <div class="field-tip">请输入 6 到 20 位数字。</div>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
          <div class="field-tip">密码至少 6 位，建议使用更复杂的组合。</div>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="律师" value="lawyer" />
            <el-option label="机构管理员" value="tenant_admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="createLawyer">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="inviteDialogVisible" title="律师邀请链接" width="560px">
      <div class="field-tip invite-tip">
        把下面的链接发给要加入机构的律师，对方打开后可直接进入加入流程。
      </div>
      <el-input :model-value="inviteLink" readonly />
      <template #footer>
        <el-button @click="copyInviteLink">复制链接</el-button>
        <el-button type="primary" @click="inviteDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { formatRole } from '../lib/displayText'
import http from '../lib/http'
import { extractFriendlyError, validateName, validatePassword, validatePhone } from '../lib/formMessages'

const lawyers = ref([])
const pendingUsers = ref([])
const dialogVisible = ref(false)
const inviteDialogVisible = ref(false)
const inviteLink = ref('')
const submitting = ref(false)
const loading = ref(false)

const form = reactive({
  real_name: '',
  phone: '',
  password: '',
  role: 'lawyer',
})

function resetForm() {
  form.real_name = ''
  form.phone = ''
  form.password = ''
  form.role = 'lawyer'
}

async function loadLawyers() {
  loading.value = true
  try {
    const [lawyersResp, pendingResp] = await Promise.all([
      http.get('/users/lawyers'),
      http.get('/users/pending'),
    ])
    lawyers.value = lawyersResp.data
    pendingUsers.value = pendingResp.data
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '律师列表加载失败'))
  } finally {
    loading.value = false
  }
}

async function createLawyer() {
  const validationMessage =
    validateName(form.real_name, '律师姓名') ||
    validatePhone(form.phone, '手机号') ||
    validatePassword(form.password, '密码')
  if (validationMessage) {
    ElMessage.warning(validationMessage)
    return
  }

  submitting.value = true
  try {
    await http.post('/users/lawyers', form)
    ElMessage.success('律师创建成功')
    dialogVisible.value = false
    resetForm()
    await loadLawyers()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '律师创建失败'))
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(user) {
  try {
    const nextStatus = user.status === 1 ? 0 : 1
    await http.patch(`/users/${user.id}/status`, { status: nextStatus })
    ElMessage.success(nextStatus === 1 ? '账号已启用' : '账号已停用')
    await loadLawyers()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '状态更新失败'))
  }
}

async function approve(userId) {
  try {
    await http.patch(`/tenants/members/${userId}/approve`)
    ElMessage.success('审批通过')
    await loadLawyers()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '审批失败'))
  }
}

async function reject(userId) {
  try {
    await http.delete(`/users/${userId}/reject`)
    ElMessage.success('已拒绝')
    await loadLawyers()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '拒绝失败'))
  }
}

async function openInviteDialog() {
  try {
    const { data } = await http.post('/users/invite-lawyer')
    inviteLink.value = `${window.location.origin}/login?invite=${data.token}`
    inviteDialogVisible.value = true
    ElMessage.success('邀请链接已生成')
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '生成邀请链接失败'))
  }
}

async function copyInviteLink() {
  try {
    await navigator.clipboard.writeText(inviteLink.value)
    ElMessage.success('邀请链接已复制')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制，请手动复制链接')
  }
}

onMounted(loadLawyers)
</script>

<style scoped>
.field-tip {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.invite-tip {
  margin-bottom: 12px;
}
</style>
