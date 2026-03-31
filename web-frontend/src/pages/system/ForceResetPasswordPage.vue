<template>
  <div class="min-h-screen flex items-center justify-center bg-background px-4 py-8">
    <div class="w-full max-w-xl rounded-3xl border border-border bg-card p-8 shadow-2xl">
      <p class="text-xs font-medium uppercase tracking-[0.2em] text-primary">安全校验</p>
      <h1 class="mt-3 text-3xl font-bold">首次登录需要先修改密码</h1>
      <p class="mt-2 text-sm leading-6 text-muted-foreground">
        当前账号 {{ maskedPhone }} 使用的是初始密码。为保障账号安全，请先设置一个包含字母和数字的新密码，再继续进入工作台。
      </p>

      <div class="mt-8 space-y-4">
        <input
          v-model="form.newPassword"
          type="password"
          maxlength="128"
          class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
          placeholder="请输入新密码，至少 8 位且同时包含字母和数字"
          @keyup.enter="submit"
        />
        <input
          v-model="form.confirmPassword"
          type="password"
          maxlength="128"
          class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
          placeholder="请再次输入新密码"
          @keyup.enter="submit"
        />
      </div>

      <button
        class="mt-6 w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
        :disabled="submitting"
        @click="submit"
      >
        <span v-if="submitting">正在提交，请稍候...</span>
        <span v-else>确认修改密码</span>
      </button>

      <div v-if="statusMessage" class="mt-5 rounded-2xl border px-4 py-3 text-sm" :class="statusClass">
        {{ statusMessage }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { extractFriendlyError, validatePassword } from '../../shared/lib/formMessages'
import { useAuthStore } from '../../features/auth/model/store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const submitting = ref(false)
const statusMessage = ref('')
const statusTone = ref('info')
const form = reactive({
  newPassword: '',
  confirmPassword: '',
})

const maskedPhone = computed(() => {
  const phone = String(authStore.currentUser?.phone || '').trim()
  if (!phone) {
    return '当前账号'
  }
  if (phone.length < 7) {
    return phone
  }
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
})

const statusClass = computed(() => {
  if (statusTone.value === 'success') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  }
  if (statusTone.value === 'error') {
    return 'border-rose-200 bg-rose-50 text-rose-700'
  }
  return 'border-amber-200 bg-amber-50 text-amber-700'
})

function getPostResetRedirect() {
  const redirect = String(route.query.redirect || '').trim()
  if (!redirect || redirect === '/force-reset-password') {
    return '/'
  }
  return redirect
}

function setStatus(message, tone = 'info') {
  statusMessage.value = message
  statusTone.value = tone
}

async function ensureResetRequired() {
  try {
    await authStore.ensureCurrentUser()
  } catch {
    await router.replace({ name: 'login', query: { redirect: '/force-reset-password' } })
    return false
  }

  if (!authStore.currentUser?.must_reset_password) {
    await router.replace(getPostResetRedirect())
    return false
  }
  return true
}

async function submit() {
  const validationMessage = validatePassword(form.newPassword, '新密码')
  if (validationMessage) {
    setStatus(validationMessage, 'error')
    return
  }
  if (form.newPassword !== form.confirmPassword) {
    setStatus('两次输入的新密码不一致。', 'error')
    return
  }

  submitting.value = true
  setStatus('')
  try {
    await authStore.changePasswordAndRebuildSession({
      newPassword: form.newPassword,
    })
    setStatus('密码已修改，正在进入工作台。', 'success')
    await router.replace(getPostResetRedirect())
  } catch (error) {
    setStatus(extractFriendlyError(error, '密码修改失败，请稍后重试。'), 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await ensureResetRequired()
})
</script>
