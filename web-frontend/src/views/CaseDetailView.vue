<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">案件详情</p>
        <h2>{{ caseDetail?.title || '加载中' }}</h2>
      </div>
      <el-button @click="$router.push('/cases')">返回列表</el-button>
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
      </div>
      <el-table :data="files" stripe>
        <el-table-column prop="file_name" label="文件名" min-width="240" />
        <el-table-column prop="file_type" label="类型" min-width="180" />
        <el-table-column label="上传人" min-width="140">
          <template #default="{ row }">
            {{ row.uploader?.real_name || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </article>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import http from '../lib/http'

const route = useRoute()
const caseDetail = ref(null)
const files = ref([])

async function loadDetail() {
  const caseId = route.params.id
  const [detailResp, filesResp] = await Promise.all([
    http.get(`/cases/${caseId}`),
    http.get(`/files/case/${caseId}`),
  ])
  caseDetail.value = detailResp.data
  files.value = filesResp.data
}

onMounted(loadDetail)
</script>
