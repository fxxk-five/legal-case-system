<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <button @click="goBack" class="p-2 rounded-full hover:bg-secondary transition-colors">
          <ArrowLeftIcon class="w-5 h-5" />
        </button>
        <div>
          <p
            v-if="fromClientDetail"
            class="text-[11px] font-medium uppercase tracking-[0.22em] text-cyan-600"
          >
            返回当事人详情
          </p>
          <p class="text-xs font-medium text-muted-foreground uppercase tracking-wider">案件详情</p>
          <h2 class="text-3xl font-bold tracking-tight">{{ caseDetail?.title || '加载中...' }}</h2>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <el-select v-model="statusForm.status" placeholder="更新状态" @change="handleUpdateStatus" class="apple-select !w-32">
          <el-option label="新建" value="new" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="done" />
        </el-select>

        <button @click="$router.push(`/cases/${$route.params.id}/ai/parse`)" class="inline-flex items-center px-4 py-2 rounded-xl bg-blue-50 text-blue-600 text-sm font-medium hover:bg-blue-100 transition-colors">
          <FileSearchIcon class="w-4 h-4 mr-2" /> AI 解析
        </button>
      </div>
    </div>

    <!-- Stats Bento -->
    <div class="bento-card !p-8">
      <div class="detail-grid">
        <div class="detail-item">
          <span class="readonly-label">案号</span>
          <span class="readonly-value text-lg">{{ caseDetail?.case_number }}</span>
          <div class="mt-2">
            <span class="apple-badge" :class="statusBadgeClass(caseDetail?.status)">
              {{ formatCaseStatus(caseDetail?.status) }}
            </span>
          </div>
        </div>
        <div class="detail-item">
          <span class="readonly-label">当事人</span>
          <span class="readonly-value text-lg">{{ formatText(caseDetail?.client?.real_name) }}</span>
          <span class="text-xs text-gray-400 mt-1">{{ formatText(caseDetail?.client?.phone) }}</span>
        </div>
        <div class="detail-item">
          <span class="readonly-label">负责律师</span>
          <span class="readonly-value text-lg">{{ formatText(caseDetail?.assigned_lawyer?.real_name) }}</span>
          <span class="text-xs text-gray-400 mt-1">{{ formatText(caseDetail?.assigned_lawyer?.phone) }}</span>
        </div>
        <div class="detail-item">
          <span class="readonly-label">法律类型</span>
          <span class="readonly-value text-lg">{{ formatLegalType(caseDetail?.legal_type) }}</span>
        </div>
        <div class="detail-item">
          <span class="readonly-label">截止时间</span>
          <span class="readonly-value text-lg">{{ formatDateTime(caseDetail?.deadline) }}</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Timeline -->
      <div class="lg:col-span-1 space-y-6">
        <div class="flex items-center justify-between">
          <h3 class="text-xl font-bold">关键进展</h3>
          <button @click="loadInvitePath" class="text-xs text-primary hover:underline">获取邀请链接</button>
        </div>

        <div v-if="invitePath" class="p-4 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-between gap-4">
          <code class="text-xs text-emerald-700 truncate flex-1">{{ invitePath }}</code>
          <button @click="copyInvitePath" class="text-xs font-bold text-emerald-600 shrink-0">复制</button>
        </div>

        <div class="bento-card !p-8">
          <el-timeline v-if="caseDetail?.timeline?.length">
            <el-timeline-item
              v-for="item in caseDetail.timeline"
              :key="`${item.event_type}-${item.occurred_at}`"
              :timestamp="item.occurred_at"
              placement="top"
              :type="item.event_type === 'status_change' ? 'primary' : ''"
            >
              <div class="space-y-1">
                <p class="font-semibold text-sm">{{ item.title }}</p>
                <p class="text-xs text-muted-foreground leading-relaxed">{{ item.description }}</p>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无时间线记录" :image-size="60" />
        </div>
      </div>

      <!-- Files -->
      <div class="lg:col-span-2 space-y-6">
        <div class="flex items-center justify-between">
          <h3 class="text-xl font-bold">案件材料</h3>
          <el-upload
            :show-file-list="false"
            :http-request="handleUpload"
            accept="*"
          >
            <button class="inline-flex items-center px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium shadow-apple hover:opacity-90 transition-all">
              <UploadIcon class="w-4 h-4 mr-2" /> 上传文件
            </button>
          </el-upload>
        </div>

        <div class="bento-card !p-0 overflow-hidden">
          <el-table v-loading="loadingFiles" :data="files" empty-text="暂无案件文件">
            <el-table-column prop="file_name" label="文件名" min-width="200">
              <template #default="{ row }">
                <div class="flex items-center gap-3">
                  <FileIcon class="w-4 h-4 text-muted-foreground" />
                  <span class="font-medium">{{ row.file_name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="file_type" label="类型" width="120" />
            <el-table-column label="上传人" width="120">
              <template #default="{ row }">
                <span class="text-sm">{{ formatText(row.uploader?.real_name) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="right">
              <template #default="{ row }">
                <div class="flex justify-end gap-2">
                  <button @click="handleDownload(row)" class="p-2 rounded-lg hover:bg-secondary text-primary transition-colors">
                    <DownloadIcon class="w-4 h-4" />
                  </button>
                  <button @click="handleDeleteFile(row.id)" class="p-2 rounded-lg hover:bg-rose-50 text-rose-600 transition-colors">
                    <TrashIcon class="w-4 h-4" />
                  </button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import {
  ArrowLeftIcon,
  FileSearchIcon,
  UploadIcon,
  FileIcon,
  DownloadIcon,
  TrashIcon
} from 'lucide-vue-next'

import { formatCaseStatus, formatLegalType, formatText } from '../lib/displayText'
import { uploadCaseFileByPolicy } from '../lib/fileUpload'
import http from '../lib/http'
import { extractFriendlyError } from '../lib/formMessages'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id
const fromClientDetail = computed(() => route.query.from === 'client' && Boolean(route.query.client_id))

const caseDetail = ref(null)
const files = ref([])
const loadingFiles = ref(false)
const invitePath = ref('')

const statusForm = reactive({
  status: '',
})

function statusBadgeClass(status) {
  switch (status) {
    case 'new': return 'apple-badge-primary'
    case 'processing': return 'apple-badge-warning'
    case 'done': return 'apple-badge-success'
    default: return 'apple-badge-neutral'
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

function goBack() {
  if (fromClientDetail.value) {
    router.push({
      name: 'client-detail',
      params: { id: route.query.client_id },
    })
    return
  }
  router.push('/cases')
}

async function loadCaseDetail() {
  try {
    const { data } = await http.get(`/cases/${caseId}`)
    caseDetail.value = data
    statusForm.status = data.status
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '案件详情加载失败'))
  }
}

async function loadFiles() {
  loadingFiles.value = true
  try {
    const { data } = await http.get(`/files/case/${caseId}`)
    files.value = data
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '文件列表加载失败'))
  } finally {
    loadingFiles.value = false
  }
}

async function handleUpdateStatus() {
  try {
    await http.patch(`/cases/${caseId}`, { status: statusForm.status })
    ElMessage.success('状态更新成功')
    loadCaseDetail()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '状态更新失败'))
  }
}

async function handleUpload({ file }) {
  try {
    await uploadCaseFileByPolicy(caseId, file)
    ElMessage.success('文件上传成功')
    loadFiles()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '文件上传失败'))
  }
}

async function handleDownload(file) {
  try {
    const { data } = await http.get(`/files/${file.id}/access-link`)
    const baseOrigin = http.defaults.baseURL.replace(/\/api\/v1$/, '')
    const url = String(data.access_url || '').startsWith('http')
      ? data.access_url
      : `${baseOrigin}${data.access_url}`
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', file.file_name)
    link.setAttribute('target', '_blank')
    link.setAttribute('rel', 'noopener')
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch {
    ElMessage.error('下载失败')
  }
}

async function handleDeleteFile() {
  ElMessage.warning('当前版本暂不支持删除文件')
}

async function loadInvitePath() {
  try {
    const { data } = await http.get(`/cases/${caseId}/invite-qrcode`)
    invitePath.value = data.path || `${window.location.origin}/invite/${data.token}`
  } catch {
    ElMessage.error('获取邀请链接失败')
  }
}

function copyInvitePath() {
  navigator.clipboard.writeText(invitePath.value)
  ElMessage.success('已复制到剪贴板')
}

onMounted(() => {
  loadCaseDetail()
  loadFiles()
})
</script>
