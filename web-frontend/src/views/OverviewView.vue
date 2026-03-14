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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import http from '../lib/http'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const tenant = ref(null)
const cases = ref([])

onMounted(async () => {
  const [tenantResp, casesResp] = await Promise.all([
    http.get('/tenants/current'),
    http.get('/cases'),
  ])
  tenant.value = tenantResp.data
  cases.value = casesResp.data
})
</script>
