<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">律师管理</h2>
        <p class="text-muted-foreground">管理机构内的律师账号与入驻审批</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="openInviteDialog"
          class="inline-flex items-center px-4 py-2.5 rounded-xl bg-secondary text-secondary-foreground text-sm font-medium hover:bg-secondary/80 transition-all"
        >
          <LinkIcon class="w-4 h-4 mr-2" /> 生成邀请链接
        </button>
      </div>
    </div>

    <!-- Active Lawyers Table -->
    <div class="space-y-4">
      <h3 class="text-xl font-bold">已启用律师</h3>
      <div class="bento-card !p-0 overflow-hidden">
        <el-table v-loading="loading" :data="lawyers" empty-text="暂无律师数据">
          <el-table-column prop="real_name" label="姓名" min-width="120">
            <template #default="{ row }">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-primary/5 flex items-center justify-center text-xs font-bold text-primary">
                  {{ row.real_name?.charAt(0) }}
                </div>
                <span class="font-medium">{{ row.real_name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="phone" label="手机号" min-width="150" />
          <el-table-column label="角色" min-width="120">
            <template #default="{ row }">
              <span class="text-sm text-muted-foreground">{{ formatRole(row.role) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="row.status === 1 ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-rose-50 text-rose-600 border border-rose-100'"
              >
                {{ row.status === 1 ? '已启用' : '已停用' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="right">
            <template #default="{ row }">
              <button
                @click="toggleStatus(row)"
                class="text-sm font-medium text-primary hover:underline decoration-primary/30 underline-offset-4"
              >
                {{ row.status === 1 ? '停用' : '启用' }}
              </button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Pending Approvals -->
    <div class="space-y-4">
      <h3 class="text-xl font-bold">待审批申请</h3>
      <div class="bento-card !p-0 overflow-hidden border-amber-100 bg-amber-50/10">
        <el-table v-loading="loading" :data="pendingUsers" empty-text="暂无待审批律师">
          <el-table-column prop="real_name" label="姓名" min-width="120" />
          <el-table-column prop="phone" label="手机号" min-width="150" />
          <el-table-column label="角色" min-width="120">
            <template #default="{ row }">
              {{ formatRole(row.role) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="right">
            <template #default="{ row }">
              <div class="flex justify-end gap-3">
                <button @click="approve(row.id)" class="text-sm font-bold text-emerald-600 hover:text-emerald-700">通过</button>
                <button @click="reject(row.id)" class="text-sm font-bold text-rose-600 hover:text-rose-700">拒绝</button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Invite Dialog -->
    <el-dialog v-model="inviteDialogVisible" title="律师邀请链接" width="520px">
      <div class="space-y-4 py-2">
        <p class="text-sm text-muted-foreground">
          将此链接发送给律师，对方打开后可直接申请加入您的机构。
        </p>
        <div class="p-4 bg-secondary/30 rounded-2xl border border-border flex items-center gap-3">
          <code class="text-xs flex-1 truncate">{{ inviteLink }}</code>
          <button @click="copyInviteLink" class="text-xs font-bold text-primary shrink-0">复制</button>
        </div>
      </div>
      <template #footer>
        <button @click="inviteDialogVisible = false" class="px-6 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium">关闭</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { ElMessageBox } from 'element-plus/es/components/message-box/index'
import { LinkIcon } from 'lucide-vue-next'

import { formatRole } from '../lib/displayText'
import http from '../lib/http'
import { extractFriendlyError } from '../lib/formMessages'

const lawyers = ref([])
const pendingUsers = ref([])
const loading = ref(false)
const inviteDialogVisible = ref(false)
const inviteLink = ref('')

async function loadData() {
  loading.value = true
  try {
    const [lawyersResp, pendingResp] = await Promise.all([
      http.get('/users/lawyers'),
      http.get('/users/pending'),
    ])
    lawyers.value = lawyersResp.data
    pendingUsers.value = pendingResp.data
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '数据加载失败'))
  } finally {
    loading.value = false
  }
}

async function toggleStatus(user) {
  const action = user.status === 1 ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}该账号吗？`, '提示')
    await http.patch(`/users/${user.id}/status`, { status: user.status === 1 ? 0 : 1 })
    ElMessage.success(`账号已${action}`)
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('操作失败')
  }
}

async function approve(userId) {
  try {
    await http.patch(`/users/${userId}/approve`)
    ElMessage.success('审批已通过')
    loadData()
  } catch {
    ElMessage.error('审批失败')
  }
}

async function reject(userId) {
  try {
    await ElMessageBox.confirm('确定要拒绝该申请吗？', '提示', { type: 'warning' })
    await http.delete(`/users/${userId}/reject`)
    ElMessage.success('已拒绝申请')
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('操作失败')
  }
}

async function openInviteDialog() {
  try {
    const { data } = await http.post('/users/invite-lawyer')
    inviteLink.value = `${window.location.origin}/login?scene=lawyer-invite&token=${encodeURIComponent(data.token)}`
    inviteDialogVisible.value = true
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '邀请链接生成失败'))
  }
}

async function copyInviteLink() {
  if (!inviteLink.value) {
    ElMessage.warning('请先生成邀请链接')
    return
  }
  await navigator.clipboard.writeText(inviteLink.value)
  ElMessage.success('邀请链接已复制')
}

onMounted(loadData)
</script>
