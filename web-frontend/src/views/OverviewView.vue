<template>
  <div class="panel-grid">
    <article class="summary-card accent">
      <p>当前租户</p>
      <h2>{{ tenant?.name || '未加载' }}</h2>
      <span>{{ tenant?.tenant_code || 'N/A' }}</span>
    </article>
    <article class="summary-card">
      <p>当前用户</p>
      <h2>{{ authStore.currentUser?.real_name || '-' }}</h2>
      <span>{{ authStore.currentUser?.phone || '-' }}</span>
    </article>
    <article class="summary-card">
      <p>案件总数</p>
      <h2>{{ cases.length }}</h2>
      <span>来自当前租户</span>
    </article>
    <article class="summary-card">
      <p>待审批律师</p>
      <h2>{{ pendingLawyers.length }}</h2>
      <span>需要管理员处理</span>
    </article>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import http from '../lib/http'
import { useAuthStore } from '../stores/auth'
import { extractFriendlyError } from '../lib/formMessages'

const authStore = useAuthStore()
const tenant = ref(null)
const cases = ref([])
const pendingLawyers = ref([])

onMounted(async () => {
  try {
    if (!authStore.currentUser) {
      await authStore.fetchCurrentUser()
    }

    const requests = [
      http.get('/tenants/current'),
      http.get('/cases'),
    ]

    if (authStore.currentUser?.is_tenant_admin || authStore.currentUser?.role === 'tenant_admin') {
      requests.push(http.get('/users/pending'))
    }

    const [tenantResp, casesResp, pendingResp] = await Promise.all(requests)
    tenant.value = tenantResp.data
    cases.value = casesResp.data
    pendingLawyers.value = pendingResp?.data || []
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '概览信息加载失败'))
  }
})
</script>
