<template>
  <div class="mx-auto max-w-3xl">
    <div class="bento-card text-center py-16 space-y-4">
      <h2 class="text-3xl font-bold tracking-tight">当事人请使用小程序</h2>
      <p class="mt-4 text-muted-foreground leading-relaxed">
        当前账号角色为当事人。根据系统角色边界，当事人仅可在小程序端上传资料与查看案件进度。
      </p>
      <p class="mt-2 text-muted-foreground leading-relaxed">
        请在微信小程序中继续操作，以确保资料上传与流程状态同步。
      </p>
      <button
        @click="handleLogout"
        class="inline-flex items-center justify-center rounded-xl border border-border px-4 py-2.5 text-sm font-medium hover:bg-secondary transition-colors"
      >
        退出当前账号
      </button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../features/auth/model/store'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout() {
  try {
    await authStore.logoutWithServer()
  } catch {
    authStore.logout()
  }
  router.replace('/login')
}
</script>
