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
        <RouterLink v-if="isAdmin" to="/admin">管理面板</RouterLink>
        <RouterLink v-if="isAdmin" to="/lawyers">律师管理</RouterLink>
        <RouterLink v-if="isAdmin" to="/settings">机构设置</RouterLink>
      </nav>
    </aside>

    <main class="dashboard-main">
      <header class="dashboard-header">
        <div>
          <p class="header-label">当前登录</p>
          <h1>{{ authStore.currentUser?.real_name || '未登录用户' }}</h1>
        </div>
        <div class="header-actions">
          <el-popover placement="bottom" :width="360" trigger="click" @show="loadNotifications">
            <template #reference>
              <el-badge :value="notificationStore.unreadCount" :hidden="notificationStore.unreadCount === 0">
                <el-button plain>通知</el-button>
              </el-badge>
            </template>

            <div class="notification-panel">
              <div class="notification-head">
                <strong>通知</strong>
                <el-button link type="primary" @click="loadNotifications">刷新</el-button>
              </div>
              <div v-if="notificationStore.items.length === 0" class="notification-empty">
                暂无通知
              </div>
              <div
                v-for="item in notificationStore.items"
                :key="item.id"
                class="notification-item"
                :class="{ unread: !item.is_read }"
              >
                <div class="notification-copy">
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.content }}</p>
                </div>
                <el-button v-if="!item.is_read" link type="primary" @click="markRead(item.id)">
                  标记已读
                </el-button>
              </div>
            </div>
          </el-popover>

          <span class="header-role">{{ formatRole(authStore.currentUser?.role) }}</span>
          <el-button plain @click="handleLogout">退出登录</el-button>
        </div>
      </header>

      <section class="dashboard-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { formatRole } from '../lib/displayText'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'

const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const router = useRouter()

const isAdmin = computed(
  () => authStore.currentUser?.is_tenant_admin || authStore.currentUser?.role === 'tenant_admin',
)

onMounted(async () => {
  await authStore.fetchCurrentUser()
  await loadNotifications()
})

async function loadNotifications() {
  await notificationStore.fetchNotifications()
}

async function markRead(notificationId) {
  await notificationStore.markRead(notificationId)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
