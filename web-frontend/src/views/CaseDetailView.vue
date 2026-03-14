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
        <el-button @click="$router.push('/cases')">返回列表</el-button>
      </div>
    </div>

    <div v-if="caseDetail" class="panel-grid detail-grid">
      <article class="summary-card">
        <p>案号</p>
        <h2>{{ caseDetail.case_number }}</h2>
        <span>状态：{{ caseDetail.status }}</span>
      </article>
      <article class="summary-card">
        <p>当事人</p>
        <h2>{{ caseDetail.client?.real_name || '-' }}</h2>
        <span>{{ caseDetail.client?.phone || '-' }}</span>
      </article>
      <article class="summary-card">
        <p>负责律师</p>
        <h2>{{ caseDetail.assigned_lawyer?.real_name || '-' }}</h2>
        <span>{{ caseDetail.assigned_lawyer?.phone || '-' }}</span>
      </article>
    </div>

    <article class="cases-page">
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

      <el-table :data="files" stripe>
        <el-table-column prop="file_name" label="文件名" min-width="240" />
        <el-table-column prop="file_type" label="类型" min-width="180" />
        <el-table-column label="上传人" min-width="140">
          <template #default="{ row }">
            {{ row.uploader?.real_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
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

import http from '../lib/http'

const route = useRoute()
const caseDetail = ref(null)
const files = ref([])
const statusForm = reactive({
  status: 'new',
})

async function loadDetail() {
  const caseId = route.params.id
  const [detailResp, filesResp] = await Promise.all([
    http.get(`/cases/${caseId}`),
    http.get(`/files/case/${caseId}`),
  ])
  caseDetail.value = detailResp.data
  statusForm.status = detailResp.data.status
  files.value = filesResp.data
}

async function handleUpload({ file }) {
  const formData = new FormData()
  formData.append('upload', file)
  try {
    await http.post(`/files/upload?case_id=${route.params.id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('文件上传成功')
    await loadDetail()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '文件上传失败')
  }
}

async function downloadFile(file) {
  try {
    const response = await http.get(`/files/${file.id}/download`, {
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

async function handleUpdateStatus() {
  try {
    await http.patch(`/cases/${route.params.id}`, { status: statusForm.status })
    ElMessage.success('案件状态已更新')
    await loadDetail()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '状态更新失败')
  }
}

onMounted(loadDetail)
</script>
