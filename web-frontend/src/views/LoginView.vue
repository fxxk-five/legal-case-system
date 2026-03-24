<template>
  <div class="min-h-screen flex items-center justify-center p-4 bg-background relative overflow-hidden">
    <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-3xl"></div>
    <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-3xl"></div>

    <div class="w-full max-w-[1180px] grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] bg-card border border-border rounded-[32px] shadow-2xl overflow-hidden relative z-10">
      <div class="p-10 lg:p-12 bg-primary text-primary-foreground flex flex-col justify-between relative overflow-hidden">
        <div class="absolute top-0 right-0 p-12 opacity-10">
          <ScaleIcon class="w-64 h-64" />
        </div>

        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/10 backdrop-blur-md rounded-xl flex items-center justify-center mb-8">
            <QrCodeIcon class="w-6 h-6 text-white" />
          </div>
          <p class="text-sm font-medium text-white/60 uppercase tracking-[0.2em] mb-4">Legal Case System</p>
          <h1 class="text-5xl font-bold leading-tight mb-6">工作台登录</h1>
          <p class="text-lg text-white/70 leading-relaxed max-w-lg">
            Web 端支持账号密码登录、短信验证码登录、微信扫码登录三种方式。账号即手机号；当事人登录后仍会被收敛到小程序入口说明页。
          </p>

          <div class="mt-8 flex flex-wrap gap-3 text-xs">
            <span class="px-3 py-2 rounded-full bg-white/10 border border-white/10">账号密码</span>
            <span class="px-3 py-2 rounded-full bg-white/10 border border-white/10">短信验证码</span>
            <span class="px-3 py-2 rounded-full bg-white/10 border border-white/10">微信扫码</span>
          </div>
        </div>

        <div class="relative z-10 mt-12">
          <div class="flex items-center gap-4 p-4 bg-white/5 rounded-2xl backdrop-blur-sm border border-white/10">
            <div class="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <SmartphoneIcon class="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p class="text-sm font-semibold">{{ inviteMode ? '邀请入口保留微信承接' : currentMethodTitle }}</p>
              <p class="text-xs text-white/50">{{ inviteMode ? '机构邀请继续通过微信小程序完成加入与审批。' : currentMethodDescription }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="p-8 lg:p-12 flex flex-col justify-between gap-6">
        <div class="space-y-6">
          <div>
            <h2 class="text-2xl font-bold">{{ inviteMode ? '邀请入口说明' : '选择登录方式' }}</h2>
            <p class="text-sm text-muted-foreground mt-1">
              {{ inviteMode ? '当前链接用于机构律师加入，Web 端不直接承载邀请注册。' : '三种方式可以并行使用；如果同手机号存在多个租户，请补充租户编码。' }}
            </p>
          </div>

          <div v-if="inviteMode" class="rounded-3xl border border-amber-200 bg-amber-50 p-6 space-y-4">
            <p class="text-sm font-semibold text-amber-800">当前链接属于机构邀请</p>
            <p class="text-sm text-amber-700 leading-6">
              请在微信中打开这条邀请链接，或把下方邀请码发送到手机微信，从小程序登录页完成机构加入。Web 端只提供说明与复制能力。
            </p>
            <div class="rounded-2xl bg-white border border-amber-100 px-4 py-3 flex items-center justify-between gap-4">
              <code class="text-xs text-amber-900 break-all">{{ inviteToken }}</code>
              <button class="shrink-0 px-3 py-2 rounded-xl border border-amber-200 text-sm font-medium hover:bg-amber-100" @click="copyInviteToken">
                复制 Token
              </button>
            </div>
          </div>

          <template v-else>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="item in loginMethods"
                :key="item.value"
                class="rounded-2xl border px-4 py-3 text-sm font-medium transition-colors"
                :class="loginMethod === item.value ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-secondary/20 text-muted-foreground hover:bg-secondary/50'"
                @click="setLoginMethod(item.value)"
              >
                {{ item.label }}
              </button>
            </div>

            <div v-if="loginMethod === 'password'" class="rounded-[28px] border border-border bg-secondary/30 p-6 space-y-4">
              <div>
                <p class="text-sm font-semibold">账号密码登录</p>
                <p class="text-xs text-muted-foreground mt-1">账号即手机号。适合已有账号并习惯密码登录的成员。</p>
              </div>

              <input
                v-model.trim="passwordForm.phone"
                type="tel"
                inputmode="numeric"
                maxlength="11"
                class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
                placeholder="账号（手机号）"
                @keyup.enter="handlePasswordLogin"
              />
              <input
                v-model="passwordForm.password"
                type="password"
                maxlength="128"
                class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
                placeholder="密码"
                @keyup.enter="handlePasswordLogin"
              />
              <input
                v-model.trim="passwordForm.tenant_code"
                maxlength="50"
                class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
                placeholder="可选：租户编码"
                @keyup.enter="handlePasswordLogin"
              />

              <button
                class="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
                :disabled="submitting === 'password'"
                @click="handlePasswordLogin"
              >
                <Loader2Icon v-if="submitting === 'password'" class="w-4 h-4 animate-spin" />
                登录工作台
              </button>
            </div>

            <div v-else-if="loginMethod === 'sms'" class="rounded-[28px] border border-border bg-secondary/30 p-6 space-y-4">
              <div>
                <p class="text-sm font-semibold">短信验证码登录</p>
                <p class="text-xs text-muted-foreground mt-1">先发送验证码，再用手机号和验证码登录。账号仍按手机号识别。</p>
              </div>

              <input
                v-model.trim="smsForm.phone"
                type="tel"
                inputmode="numeric"
                maxlength="11"
                class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
                placeholder="手机号"
              />

              <div class="grid grid-cols-[1fr_auto] gap-3">
                <input
                  v-model.trim="smsForm.code"
                  inputmode="numeric"
                  maxlength="6"
                  class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
                  placeholder="6 位验证码"
                  @keyup.enter="handleSmsLogin"
                />
                <button
                  class="rounded-2xl border border-border bg-white px-4 py-3 text-sm font-medium transition-colors hover:bg-secondary disabled:opacity-60"
                  :disabled="smsSending || smsCooldown > 0"
                  @click="sendLoginCode"
                >
                  {{ smsButtonLabel }}
                </button>
              </div>

              <input
                v-model.trim="smsForm.tenant_code"
                maxlength="50"
                class="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm outline-none focus:border-primary"
                placeholder="可选：租户编码"
                @keyup.enter="handleSmsLogin"
              />

              <button
                class="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
                :disabled="submitting === 'sms'"
                @click="handleSmsLogin"
              >
                <Loader2Icon v-if="submitting === 'sms'" class="w-4 h-4 animate-spin" />
                验证码登录
              </button>
            </div>

            <div v-else class="rounded-[28px] border border-border bg-secondary/30 p-6">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <p class="text-sm font-semibold">微信扫码登录</p>
                  <p class="text-xs text-muted-foreground mt-1">首次扫码会在手机上继续完成微信手机号授权。</p>
                </div>
                <button
                  class="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-border text-sm font-medium hover:bg-secondary disabled:opacity-50"
                  :disabled="loading"
                  @click="createTicket"
                >
                  <RefreshCwIcon class="w-4 h-4" />
                  刷新二维码
                </button>
              </div>

              <div class="rounded-[24px] bg-white border border-border p-5 flex flex-col items-center justify-center min-h-[360px]">
                <div v-if="loading" class="text-center space-y-4">
                  <Loader2Icon class="w-8 h-8 animate-spin mx-auto text-primary" />
                  <p class="text-sm text-muted-foreground">正在生成登录二维码...</p>
                </div>

                <template v-else-if="qrCodeUrl">
                  <img :src="qrCodeUrl" alt="微信扫码登录二维码" class="w-72 h-72 object-contain rounded-2xl border border-border" />
                  <p class="mt-4 text-xs text-muted-foreground">状态：{{ qrStatusLabel }}</p>
                  <p v-if="expiresInText" class="mt-1 text-xs text-muted-foreground">{{ expiresInText }}</p>
                </template>

                <div v-else class="text-center text-sm text-muted-foreground">未生成二维码，请点击“刷新二维码”。</div>
              </div>
            </div>
          </template>

          <div v-if="statusMessage" class="rounded-2xl border px-4 py-3 text-sm" :class="statusClass">
            {{ statusMessage }}
          </div>
        </div>

        <div class="pt-6 border-t border-border text-center">
          <p class="text-xs text-muted-foreground">&copy; 2026 Legal Case System. All rights reserved.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { Loader2Icon, QrCodeIcon, RefreshCwIcon, ScaleIcon, SmartphoneIcon } from 'lucide-vue-next'

import http from '../lib/http'
import {
  extractFriendlyError,
  validatePassword,
  validatePhone,
  validateSmsCode,
  validateTenantCode,
} from '../lib/formMessages'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loginMethods = [
  { value: 'password', label: '账号密码' },
  { value: 'sms', label: '短信验证码' },
  { value: 'wechat', label: '微信扫码' },
]

const inviteMode = computed(() => String(route.query.scene || '') === 'lawyer-invite' && Boolean(String(route.query.token || '')))
const inviteToken = computed(() => String(route.query.token || ''))

const loginMethod = ref('password')
const passwordForm = ref({
  phone: '',
  password: '',
  tenant_code: '',
})
const smsForm = ref({
  phone: '',
  code: '',
  tenant_code: '',
})

const submitting = ref('')
const smsSending = ref(false)
const smsCooldown = ref(0)
let smsCooldownTimer = null

const ticket = ref('')
const qrCodeUrl = ref('')
const loading = ref(false)
const exchanging = ref(false)
const qrStatus = ref('pending')
const expiresAt = ref('')
let pollTimer = null

const statusMessage = ref('')
const statusTone = ref('info')

const currentMethodTitle = computed(() => {
  if (loginMethod.value === 'sms') return '短信验证码登录已启用'
  if (loginMethod.value === 'wechat') return '微信扫码登录已启用'
  return '账号密码登录已启用'
})

const currentMethodDescription = computed(() => {
  if (loginMethod.value === 'sms') {
    return '发送一次性验证码即可登录，适合临时设备或忘记密码的场景。'
  }
  if (loginMethod.value === 'wechat') {
    return '浏览器生成二维码，小程序确认后自动换取 Web 登录态。'
  }
  return '账号即手机号，可直接用密码进入工作台。'
})

const qrStatusLabel = computed(() => {
  switch (qrStatus.value) {
    case 'pending':
      return '等待扫码'
    case 'confirmed':
      return '已扫码，正在登录'
    case 'consumed':
      return '已完成登录'
    case 'expired':
      return '二维码已过期'
    default:
      return qrStatus.value || '处理中'
  }
})

const expiresInText = computed(() => {
  if (!expiresAt.value) {
    return ''
  }
  const ms = new Date(expiresAt.value).getTime() - Date.now()
  if (Number.isNaN(ms) || ms <= 0) {
    return '二维码已过期，请刷新'
  }
  const seconds = Math.max(0, Math.floor(ms / 1000))
  return `二维码剩余 ${seconds}s`
})

const smsButtonLabel = computed(() => {
  if (smsSending.value) {
    return '发送中...'
  }
  if (smsCooldown.value > 0) {
    return `${smsCooldown.value}s 后重发`
  }
  return '发送验证码'
})

const statusClass = computed(() => {
  if (statusTone.value === 'success') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  }
  if (statusTone.value === 'warning') {
    return 'border-amber-200 bg-amber-50 text-amber-700'
  }
  if (statusTone.value === 'error') {
    return 'border-rose-200 bg-rose-50 text-rose-700'
  }
  return 'border-border bg-secondary/40 text-foreground'
})

function setStatus(message, tone = 'info') {
  statusMessage.value = message
  statusTone.value = tone
}

function clearStatus() {
  statusMessage.value = ''
  statusTone.value = 'info'
}

function buildAbsoluteUrl(path) {
  if (!path) return ''
  if (String(path).startsWith('http')) return path
  const origin = http.defaults.baseURL.replace(/\/api\/v1$/, '')
  return `${origin}${path}`
}

function clearPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  clearPolling()
  pollTimer = setInterval(() => {
    pollTicketStatus()
  }, 2000)
}

function startSmsCooldown(seconds) {
  const nextSeconds = Number(seconds || 0)
  if (Number.isNaN(nextSeconds) || nextSeconds <= 0) {
    smsCooldown.value = 0
    return
  }
  smsCooldown.value = nextSeconds
  if (smsCooldownTimer) {
    clearInterval(smsCooldownTimer)
  }
  smsCooldownTimer = setInterval(() => {
    if (smsCooldown.value <= 1) {
      clearInterval(smsCooldownTimer)
      smsCooldownTimer = null
      smsCooldown.value = 0
      return
    }
    smsCooldown.value -= 1
  }, 1000)
}

function clearSmsCooldown() {
  if (smsCooldownTimer) {
    clearInterval(smsCooldownTimer)
    smsCooldownTimer = null
  }
  smsCooldown.value = 0
}

function validateOptionalTenantCode(value) {
  return validateTenantCode(value, { required: false })
}

async function redirectAfterLogin() {
  const redirect = String(route.query.redirect || '')
  await router.replace(redirect || '/')
}

async function handlePasswordLogin() {
  const phoneError = validatePhone(passwordForm.value.phone, '账号（手机号）')
  const passwordError = validatePassword(passwordForm.value.password)
  const tenantCodeError = validateOptionalTenantCode(passwordForm.value.tenant_code)
  const firstError = phoneError || passwordError || tenantCodeError
  if (firstError) {
    setStatus(firstError, 'warning')
    return
  }

  submitting.value = 'password'
  clearStatus()
  try {
    await authStore.loginByPassword(passwordForm.value)
    await redirectAfterLogin()
  } catch (error) {
    setStatus(extractFriendlyError(error, '账号密码登录失败，请稍后重试'), 'warning')
  } finally {
    submitting.value = ''
  }
}

async function sendLoginCode() {
  const phoneError = validatePhone(smsForm.value.phone)
  const tenantCodeError = validateOptionalTenantCode(smsForm.value.tenant_code)
  const firstError = phoneError || tenantCodeError
  if (firstError) {
    setStatus(firstError, 'warning')
    return
  }

  smsSending.value = true
  clearStatus()
  try {
    const { data } = await http.post(
      '/auth/sms/send',
      {
        phone: smsForm.value.phone.trim(),
        purpose: 'login',
      },
      { skipAuthRefresh: true },
    )
    startSmsCooldown(data.retry_after_seconds || 60)
    setStatus('验证码已发送，请注意查收短信并在 5 分钟内完成登录。', 'success')
    ElMessage.success('验证码已发送')
  } catch (error) {
    setStatus(extractFriendlyError(error, '验证码发送失败，请稍后重试'), 'warning')
  } finally {
    smsSending.value = false
  }
}

async function handleSmsLogin() {
  const phoneError = validatePhone(smsForm.value.phone)
  const codeError = validateSmsCode(smsForm.value.code)
  const tenantCodeError = validateOptionalTenantCode(smsForm.value.tenant_code)
  const firstError = phoneError || codeError || tenantCodeError
  if (firstError) {
    setStatus(firstError, 'warning')
    return
  }

  submitting.value = 'sms'
  clearStatus()
  try {
    await authStore.loginBySmsCode(smsForm.value)
    await redirectAfterLogin()
  } catch (error) {
    setStatus(extractFriendlyError(error, '短信验证码登录失败，请稍后重试'), 'warning')
  } finally {
    submitting.value = ''
  }
}

async function exchangeLogin() {
  if (!ticket.value || exchanging.value) {
    return
  }
  exchanging.value = true
  try {
    const { data } = await http.post(
      `/auth/web-wechat-login/${encodeURIComponent(ticket.value)}/exchange`,
      {},
      { skipAuthRefresh: true },
    )
    clearPolling()
    qrStatus.value = 'consumed'
    setStatus('扫码登录成功，正在进入工作台。', 'success')
    await authStore.applyTokens(data.access_token, data.refresh_token || '')
    await redirectAfterLogin()
  } catch (error) {
    setStatus(extractFriendlyError(error, '电脑端登录兑换失败，请刷新二维码后重试'), 'warning')
  } finally {
    exchanging.value = false
  }
}

async function pollTicketStatus() {
  if (!ticket.value || exchanging.value) {
    return
  }
  try {
    const { data } = await http.get(
      `/auth/web-wechat-login/${encodeURIComponent(ticket.value)}`,
      { skipAuthRefresh: true },
    )
    qrStatus.value = data.status || 'pending'
    expiresAt.value = data.expires_at || ''
    if (data.can_exchange) {
      setStatus('已在手机端确认，正在同步浏览器登录态。', 'success')
      await exchangeLogin()
      return
    }
    if (data.status === 'expired') {
      clearPolling()
      setStatus('二维码已过期，请刷新后重新扫码。', 'warning')
    }
  } catch (error) {
    clearPolling()
    setStatus(extractFriendlyError(error, '二维码状态查询失败，请刷新后重试'), 'warning')
  }
}

async function createTicket() {
  clearPolling()
  loading.value = true
  clearStatus()
  try {
    const { data } = await http.post('/auth/web-wechat-login', {}, { skipAuthRefresh: true })
    ticket.value = data.ticket
    qrCodeUrl.value = buildAbsoluteUrl(data.qr_code_url)
    qrStatus.value = data.status || 'pending'
    expiresAt.value = data.expires_at || ''
    startPolling()
  } catch (error) {
    qrCodeUrl.value = ''
    ticket.value = ''
    setStatus(extractFriendlyError(error, '二维码生成失败，请稍后重试'), 'warning')
  } finally {
    loading.value = false
  }
}

function setLoginMethod(method) {
  if (loginMethod.value === method) {
    return
  }
  loginMethod.value = method
}

async function copyInviteToken() {
  if (!inviteToken.value) {
    return
  }
  await navigator.clipboard.writeText(inviteToken.value)
  ElMessage.success('邀请码 Token 已复制')
}

watch(loginMethod, async (nextMethod) => {
  clearStatus()
  if (inviteMode.value) {
    return
  }
  if (nextMethod === 'wechat') {
    if (!ticket.value || !qrCodeUrl.value || qrStatus.value === 'expired') {
      await createTicket()
      return
    }
    if (!pollTimer && qrStatus.value === 'pending') {
      startPolling()
    }
    return
  }
  clearPolling()
})

onMounted(async () => {
  if (!inviteMode.value && authStore.token) {
    try {
      await authStore.ensureCurrentUser()
      await redirectAfterLogin()
      return
    } catch {
      authStore.logout()
    }
  }
})

onBeforeUnmount(() => {
  clearPolling()
  clearSmsCooldown()
})
</script>
