<template>
  <div class="min-h-screen bg-background flex">
    <aside class="hidden lg:flex w-64 border-r border-border bg-card/50 backdrop-blur-xl flex-col sticky top-0 h-screen transition-all duration-300">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-foreground font-bold text-lg shadow-apple">
          LC
        </div>
        <div>
          <h2 class="font-semibold text-foreground tracking-tight">案件系统</h2>
          <p class="text-xs text-muted-foreground">Web 端</p>
        </div>
      </div>

      <nav class="flex-1 px-4 py-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors hover:bg-secondary hover:text-secondary-foreground group"
          :class="[route.path === item.to ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground']"
        >
          <component :is="item.iconComponent" class="w-4 h-4" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="p-4 border-t border-border">
        <div class="flex items-center gap-3 px-2 py-2">
          <div class="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-xs font-medium">
            {{ authStore.currentUser?.real_name?.charAt(0) || 'U' }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium truncate">{{ authStore.currentUser?.real_name }}</p>
            <p class="text-xs text-muted-foreground truncate">{{ formatRole(authStore.currentUser?.role) }}</p>
          </div>
        </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col min-w-0">
      <header class="h-16 border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-10 px-4 lg:px-8 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <button @click="mobileMenuOpen = true" class="lg:hidden p-2 -ml-2 rounded-md hover:bg-secondary">
            <MenuIcon class="w-6 h-6" />
          </button>
          <h1 class="text-lg font-semibold tracking-tight">{{ currentRouteTitle }}</h1>
        </div>

        <div class="flex items-center gap-4">
          <el-popover placement="bottom-end" :width="380" trigger="click" @show="loadNotifications" popper-class="apple-popover">
            <template #reference>
              <button class="relative p-2 rounded-full hover:bg-secondary transition-colors">
                <BellIcon class="w-5 h-5 text-muted-foreground" />
                <span v-if="notificationStore.unreadCount > 0" class="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full border-2 border-background"></span>
              </button>
            </template>

            <div class="p-4">
              <div class="flex items-center justify-between mb-4">
                <h3 class="font-semibold">通知</h3>
                <button class="text-xs text-primary hover:underline" @click="loadNotifications">刷新</button>
              </div>

              <div v-if="notificationStore.items.length === 0" class="py-8 text-center text-muted-foreground text-sm">
                暂无通知
              </div>

              <div class="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                <div
                  v-for="item in notificationStore.items"
                  :key="item.id"
                  class="p-3 rounded-xl border border-border transition-colors hover:bg-secondary/50 relative group"
                  :class="{ 'bg-secondary/30': !item.is_read }"
                >
                  <div class="flex justify-between items-start gap-2">
                    <div class="space-y-1">
                      <p class="text-sm font-medium leading-none">{{ item.title }}</p>
                      <p class="text-xs text-muted-foreground leading-relaxed">{{ item.content }}</p>
                    </div>
                    <button
                      v-if="!item.is_read"
                      @click="markRead(item.id)"
                      class="text-[10px] font-bold text-primary opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      标记已读
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </el-popover>

          <div class="h-4 w-px bg-border"></div>

          <button
            @click="handleLogout"
            class="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            退出登录
          </button>
        </div>
      </header>

      <section class="p-4 lg:p-8 max-w-7xl mx-auto w-full">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </section>
    </main>

    <transition name="fade">
      <div v-if="mobileMenuOpen" class="fixed inset-0 z-50 lg:hidden">
        <div class="absolute inset-0 bg-background/80 backdrop-blur-sm" @click="mobileMenuOpen = false"></div>
        <aside class="absolute inset-y-0 left-0 w-64 bg-card border-r border-border shadow-2xl flex flex-col">
          <div class="p-6 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-bold shadow-apple">LC</div>
              <span class="font-semibold">案件系统</span>
            </div>
            <button @click="mobileMenuOpen = false" class="p-1 rounded-full hover:bg-secondary">
              <XIcon class="w-5 h-5" />
            </button>
          </div>
          <nav class="flex-1 px-4 py-2 space-y-1">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              @click="mobileMenuOpen = false"
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors hover:bg-secondary"
              :class="[route.path === item.to ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground']"
            >
              <component :is="item.iconComponent" class="w-4 h-4" />
              {{ item.label }}
            </RouterLink>
          </nav>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboardIcon,
  BriefcaseIcon,
  UserIcon,
  UsersIcon,
  ShieldIcon,
  Building2Icon,
  BellIcon,
  MenuIcon,
  XIcon,
} from 'lucide-vue-next'

import { getVisibleNavItems } from '../lib/accessControl'
import { formatRole } from '../lib/displayText'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'

const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const router = useRouter()
const route = useRoute()
const mobileMenuOpen = ref(false)

const ICON_MAP = {
  LayoutDashboardIcon,
  BriefcaseIcon,
  UserIcon,
  UsersIcon,
  ShieldIcon,
  Building2Icon,
}

const navItems = computed(() => {
  return getVisibleNavItems(authStore.currentUser).map((item) => ({
    ...item,
    iconComponent: ICON_MAP[item.icon] || LayoutDashboardIcon,
  }))
})

const currentRouteTitle = computed(() => {
  return route.meta?.title || '详情'
})

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

async function handleLogout() {
  await authStore.logoutWithServer()
  router.push('/login')
}
</script>

<style>
.apple-popover {
  @apply !rounded-2xl !p-0 !border !border-gray-100 !shadow-apple-hover !bg-white/95 !backdrop-blur-xl;
}
</style>
