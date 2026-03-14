<template>
  <div class="dashboard-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">LC</span>
        <div>
          <h2>案件系统</h2>
          <p>试点后台</p>
        </div>
      </div>

      <nav class="nav-links">
        <RouterLink to="/">概览</RouterLink>
        <RouterLink to="/cases">案件列表</RouterLink>
      </nav>
    </aside>

    <main class="dashboard-main">
      <header class="dashboard-header">
        <div>
          <p class="header-label">当前登录</p>
          <h1>{{ authStore.currentUser?.real_name || '未登录用户' }}</h1>
        </div>
        <div class="header-actions">
          <span class="header-role">{{ authStore.currentUser?.role || '-' }}</span>
          <el-button plain @click="handleLogout">退出</el-button>
        </div>
      </header>

      <section class="dashboard-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

onMounted(() => {
  authStore.fetchCurrentUser()
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
