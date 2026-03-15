<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">案件详情</p>
        <h2>{{ caseDetail?.title || '加载中' }}</h2>
      </div>
      <div class="toolbar">
        <el-select v-model="statusForm.status" placeholder="更新状态" @change="handleUpdateStatus">
          <el-option label="新建" value="new" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="done" />
        </el-select>
        <el-button @click="loadInvitePath">获取当事人邀请</el-button>
        <el-button @click="$router.push('/cases')">返回列表</el-button>
      </div>
    </div>

    <div v-if="caseDetail" class="panel-grid detail-grid">
      <article class="summary-card">
        <p>案号</p>
        <h2>{{ caseDetail.case_number }}</h2>
        <span>状态：{{ formatCaseStatus(caseDetail.status) }}</span>
      </article>
      <article class="summary-card">
        <p>当事人</p>
        <h2>{{ formatText(caseDetail.client?.real_name) }}</h2>
        <span>{{ formatText(caseDetail.client?.phone) }}</span>
      </article>
      <article class="summary-card">
        <p>负责律师</p>
        <h2>{{ formatText(caseDetail.assigned_lawyer?.real_name) }}</h2>
        <span>{{ formatText(caseDetail.assigned_lawyer?.phone) }}</span>
      </article>
    </div>

    <article class="cases-page">
      <div class="section-heading">
        <div>
          <p class="header-label">案件时间线</p>
          <h2>关键进展</h2>
        </div>
      </div>

      <el-timeline v-if="caseDetail?.timeline?.length">
        <el-timeline-item
          v-for="item in caseDetail.timeline"
          :key="`${item.event_type}-${item.occurred_at}`"
          :timestamp="item.occurred_at"
        >
          <strong>{{ item.title }}</strong>
          <div>{{ item.description }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无时间线记录" />
    </article>

    <article class="cases-page">
      <el-alert
        v-if="invitePath"
        title="当事人邀请路径"
        type="success"
        :closable="false"
        show-icon
        class="invite-alert"
      >
        <template #default>
          <div class="invite-copy">
            <span>{{ invitePath }}</span>
            <el-button link type="primary" @click="copyInvitePath">复制</el-button>
          </div>
        </template>
      </el-alert>
      <div class="section-heading">
        <div>
          <p class="header-label">文件</p>
          <h2>案件材料</h2>
        </div>
        <el-upload
          :show-file-list="false"
          :http-request="handleUpload"
          accept="*"
        >
          <el-button type="primary">上传文件</el-button>
        </el-upload>
      </div>

      <el-table v-loading="loadingFiles" :data="files" stripe empty-text="暂无案件文件">
        <el-table-column prop="file_name" label="文件名" min-width="240" />
        <el-table-column prop="file_type" label="类型" min-width="180" />
        <el-table-column label="上传人" min-width="140">
          <template #default="{ row }">
            {{ formatText(row.uploader?.real_name) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button link @click="previewFile(row)">预览</el-button>
            <el-button link type="primary" @click="downloadFile(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { formatCaseStatus, formatText } from '../lib/displayText'
import http from '../lib/http'
import { extractFriendlyError } from '../lib/formMessages'

const route = useRoute()
const caseDetail = ref(null)
const files = ref([])
const loadingFiles = ref(false)
const loadingDetail = ref(false)
const invitePath = ref('')
const statusForm = reactive({
  status: 'new',
})

async function loadDetail() {
  const caseId = route.params.id
  loadingDetail.value = true
  loadingFiles.value = true
  try {
    const [detailResp, filesResp] = await Promise.all([
      http.get(`/cases/${caseId}`),
      http.get(`/files/case/${caseId}`),
    ])
    caseDetail.value = detailResp.data
    statusForm.status = detailResp.data.status
    files.value = filesResp.data
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '案件详情加载失败'))
  } finally {
    loadingDetail.value = false
    loadingFiles.value = false
  }
}

async function handleUpload({ file }) {
  try {
    const { data: policy } = await http.get('/files/upload-policy', {
      params: {
        case_id: route.params.id,
        file_name: file.name,
        content_type: file.type || 'application/octet-stream',
      },
    })
    const formData = new FormData()
    Object.entries(policy.form_fields || {}).forEach(([key, value]) => {
      formData.append(key, value)
    })
    formData.append(policy.file_field_name || 'upload', file)
    await http.request({
      url: policy.upload_url.replace('/api/v1', ''),
      method: policy.method || 'POST',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('文件上传成功')
    await loadDetail()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '文件上传失败'))
  }
}

async function downloadFile(file) {
  try {
    const { data: access } = await http.get(`/files/${file.id}/access-link`)
    const response = await http.get(access.access_url.replace('/api/v1', ''), {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = file.file_name
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('文件下载失败')
  }
}

async function previewFile(file) {
  try {
    const { data: access } = await http.get(`/files/${file.id}/access-link`)
    const response = await http.get(access.access_url.replace('/api/v1', ''), {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(response.data)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => window.URL.revokeObjectURL(url), 60000)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '文件预览失败'))
  }
}

async function loadInvitePath() {
  try {
    const { data } = await http.get(`/cases/${route.params.id}/invite-qrcode`)
    invitePath.value = data.path
    ElMessage.success('已生成当事人邀请路径')
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '获取邀请失败'))
  }
}

async function copyInvitePath() {
  try {
    await navigator.clipboard.writeText(invitePath.value)
    ElMessage.success('邀请路径已复制')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制，请手动复制')
  }
}

async function handleUpdateStatus() {
  try {
    await http.patch(`/cases/${route.params.id}`, { status: statusForm.status })
    ElMessage.success('案件状态已更新')
    await loadDetail()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '状态更新失败'))
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.invite-alert {
  margin-bottom: 20px;
}

.invite-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  word-break: break-all;
}
</style>
