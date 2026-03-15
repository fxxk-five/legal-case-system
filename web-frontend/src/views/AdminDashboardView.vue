<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">管理员</p>
        <h2>管理面板</h2>
      </div>
      <el-button :loading="loading" @click="loadStats">刷新</el-button>
    </div>

    <div class="panel-grid">
      <article class="summary-card accent">
        <p>律师总数</p>
        <h2>{{ stats.lawyer_count }}</h2>
        <span>当前机构已开通账号</span>
      </article>
      <article class="summary-card">
        <p>案件总数</p>
        <h2>{{ stats.case_count }}</h2>
        <span>系统中的案件记录</span>
      </article>
      <article class="summary-card">
        <p>待审批律师</p>
        <h2>{{ stats.pending_lawyer_count }}</h2>
        <span>等待管理员审核</span>
      </article>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import http from '../lib/http'
import { extractFriendlyError } from '../lib/formMessages'

const stats = reactive({
  lawyer_count: 0,
  case_count: 0,
  pending_lawyer_count: 0,
})
const loading = ref(false)

async function loadStats() {
  loading.value = true
  try {
    const { data } = await http.get('/stats/dashboard')
    Object.assign(stats, data)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '统计数据加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>
