<template>
  <div class="space-y-8">
    <section class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Super Admin</p>
        <h2 class="mt-2 text-3xl font-bold tracking-tight text-slate-900">平台概览</h2>
        <p class="mt-2 text-sm text-slate-500">
          超级管理员从这里查看租户规模、账号分布，以及“手机号统一身份”的治理规则。
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <button class="apple-btn-secondary" @click="router.push('/super-admin/tenants')">
          进入租户管理
        </button>
        <button class="apple-btn-primary" :disabled="loading" @click="loadPlatformData">
          <RefreshCwIcon class="h-4 w-4" :class="{ 'animate-spin': loading }" />
          刷新数据
        </button>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">租户总数</p>
        <div class="mt-3 flex items-end gap-2">
          <h3 class="text-4xl font-bold text-slate-900">{{ tenantSummary.total }}</h3>
          <span class="apple-badge apple-badge-primary">{{ tenantSummary.organization }} 个机构</span>
        </div>
        <p class="mt-4 text-xs text-slate-500">
          个人空间 {{ tenantSummary.personal }} 个，正常租户 {{ tenantSummary.active }} 个。
        </p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">全局账号数</p>
        <div class="mt-3 flex items-end gap-2">
          <h3 class="text-4xl font-bold text-slate-900">{{ userSummary.total }}</h3>
          <span class="apple-badge apple-badge-success">{{ userSummary.active }} 个正常</span>
        </div>
        <p class="mt-4 text-xs text-slate-500">
          待审批 {{ userSummary.pending }} 个，停用 {{ userSummary.disabled }} 个。
        </p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">角色分布</p>
        <div class="mt-3 flex items-end gap-2">
          <h3 class="text-4xl font-bold text-slate-900">{{ userSummary.lawyers }}</h3>
          <span class="apple-badge apple-badge-neutral">律师</span>
        </div>
        <p class="mt-4 text-xs text-slate-500">
          管理员 {{ userSummary.tenantAdmins }} 个，当事人 {{ userSummary.clients }} 个。
        </p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">身份治理规则</p>
        <div class="mt-3 flex items-end gap-2">
          <h3 class="text-4xl font-bold text-slate-900">{{ phonePolicies.length }}</h3>
          <span class="apple-badge apple-badge-warning">核心规则</span>
        </div>
        <p class="mt-4 text-xs text-slate-500">
          手机号是账号主标识，微信/SMS/密码只是登录通道，不是三套身份体系。
        </p>
      </article>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_0.85fr]">
      <article class="bento-card border border-slate-200/80 bg-white">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h3 class="text-lg font-semibold text-slate-900">最新租户</h3>
            <p class="mt-1 text-sm text-slate-500">快速查看新开通、停用和归档的租户状态。</p>
          </div>
          <button class="text-sm text-primary hover:underline" @click="router.push('/super-admin/tenants')">
            查看全部
          </button>
        </div>

        <div class="mt-6 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="text-left text-slate-500">
              <tr class="border-b border-slate-200">
                <th class="pb-3 font-medium">租户</th>
                <th class="pb-3 font-medium">类型</th>
                <th class="pb-3 font-medium">状态</th>
                <th class="pb-3 font-medium">编码</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="tenant in recentTenants"
                :key="tenant.id"
                class="border-b border-slate-100 last:border-0"
              >
                <td class="py-3">
                  <div class="font-medium text-slate-900">{{ tenant.name }}</div>
                  <div class="text-xs text-slate-500">租户 ID #{{ tenant.id }}</div>
                </td>
                <td class="py-3">{{ formatTenantType(tenant.type) }}</td>
                <td class="py-3">
                  <span class="apple-badge" :class="tenantStatusClass(tenant.status)">
                    {{ formatTenantStatus(tenant.status) }}
                  </span>
                </td>
                <td class="py-3 font-mono text-xs text-slate-600">{{ tenant.tenant_code }}</td>
              </tr>
              <tr v-if="!recentTenants.length">
                <td colspan="4" class="py-8 text-center text-slate-500">暂无租户数据。</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <h3 class="text-lg font-semibold text-slate-900">统一身份规则</h3>
        <div class="mt-5 space-y-4">
          <div
            v-for="item in phonePolicies"
            :key="item.title"
            class="rounded-2xl border border-slate-200 bg-slate-50/70 p-4"
          >
            <div class="font-medium text-slate-900">{{ item.title }}</div>
            <p class="mt-1 text-sm text-slate-500">{{ item.description }}</p>
          </div>
        </div>
      </article>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <article class="bento-card border border-slate-200/80 bg-white">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h3 class="text-lg font-semibold text-slate-900">角色占比</h3>
            <p class="mt-1 text-sm text-slate-500">用于检查平台账号结构是否健康。</p>
          </div>
          <button class="text-sm text-primary hover:underline" @click="router.push('/super-admin/users')">
            查看用户总览
          </button>
        </div>

        <div class="mt-6 space-y-4">
          <div v-for="item in roleBreakdown" :key="item.key">
            <div class="mb-2 flex items-center justify-between text-sm">
              <span class="text-slate-700">{{ item.label }}</span>
              <span class="font-medium text-slate-900">{{ item.count }}</span>
            </div>
            <div class="h-2 rounded-full bg-slate-100">
              <div class="h-2 rounded-full bg-primary transition-all" :style="{ width: `${item.percent}%` }"></div>
            </div>
          </div>
        </div>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <h3 class="text-lg font-semibold text-slate-900">最新账号</h3>
        <p class="mt-1 text-sm text-slate-500">用于排查待审批账号、跨租户账号和身份绑定情况。</p>
        <div class="mt-6 space-y-3">
          <div
            v-for="user in recentUsers"
            :key="user.id"
            class="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50/40 p-4 md:flex-row md:items-center md:justify-between"
          >
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-medium text-slate-900">{{ user.real_name || '未命名账号' }}</span>
                <span class="apple-badge" :class="userStatusClass(user.status)">
                  {{ formatUserStatus(user.status) }}
                </span>
              </div>
              <p class="mt-1 text-sm text-slate-500">
                {{ formatRole(user.role) }} · {{ user.phone }} · 租户 #{{ user.tenant_id }}
              </p>
            </div>
            <div class="text-xs text-slate-500">用户 ID #{{ user.id }}</div>
          </div>
          <div v-if="!recentUsers.length" class="py-6 text-center text-sm text-slate-500">
            暂无用户数据。
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { RefreshCwIcon } from 'lucide-vue-next'

import { formatRole, formatTenantStatus, formatTenantType, formatUserStatus } from '../lib/displayText'
import { extractFriendlyError } from '../lib/formMessages'
import http from '../lib/http'

const router = useRouter()
const loading = ref(false)
const tenants = ref([])
const users = ref([])

const phonePolicies = [
  {
    title: '手机号是租户内统一账号主键',
    description:
      '平台层允许同一手机号出现在不同租户，但在同一租户内必须唯一，防止邀请绑案和登录命中错误账号。',
  },
  {
    title: '微信一键登录、短信验证码、账号密码必须回到同一账号',
    description:
      '三种方式都是登录通道，不允许各自创建独立身份；只要手机号和租户落点一致，就应落到同一个用户记录。',
  },
  {
    title: '邀请 token 只负责落点，不负责生成第二身份',
    description:
      '律师首次邀请当事人时提供的是 tenant/case 绑定上下文；当事人完成登录或注册后，再按手机号把账号和案件关联起来。',
  },
]

const tenantSummary = computed(() => ({
  total: tenants.value.length,
  active: tenants.value.filter((item) => Number(item.status) === 1).length,
  organization: tenants.value.filter((item) => item.type === 'organization').length,
  personal: tenants.value.filter((item) => item.type === 'personal').length,
}))

const userSummary = computed(() => ({
  total: users.value.length,
  active: users.value.filter((item) => Number(item.status) === 1).length,
  pending: users.value.filter((item) => Number(item.status) === 0).length,
  disabled: users.value.filter((item) => Number(item.status) === 2).length,
  tenantAdmins: users.value.filter((item) => item.role === 'tenant_admin').length,
  lawyers: users.value.filter((item) => item.role === 'lawyer').length,
  clients: users.value.filter((item) => item.role === 'client').length,
}))

const recentTenants = computed(() => {
  return [...tenants.value].sort((left, right) => Number(right.id) - Number(left.id)).slice(0, 6)
})

const recentUsers = computed(() => {
  return [...users.value].sort((left, right) => Number(right.id) - Number(left.id)).slice(0, 6)
})

const roleBreakdown = computed(() => {
  const total = Math.max(users.value.length, 1)
  const rows = [
    { key: 'super_admin', label: '超级管理员', count: users.value.filter((item) => item.role === 'super_admin').length },
    { key: 'tenant_admin', label: '机构管理员', count: users.value.filter((item) => item.role === 'tenant_admin').length },
    { key: 'lawyer', label: '律师', count: users.value.filter((item) => item.role === 'lawyer').length },
    { key: 'client', label: '当事人', count: users.value.filter((item) => item.role === 'client').length },
  ]

  return rows.map((item) => ({
    ...item,
    percent: Math.round((item.count / total) * 100),
  }))
})

function tenantStatusClass(status) {
  switch (Number(status)) {
    case 1:
      return 'apple-badge-success'
    case 2:
      return 'apple-badge-warning'
    case 3:
      return 'apple-badge-danger'
    default:
      return 'apple-badge-neutral'
  }
}

function userStatusClass(status) {
  switch (Number(status)) {
    case 1:
      return 'apple-badge-success'
    case 2:
      return 'apple-badge-warning'
    case 3:
      return 'apple-badge-danger'
    default:
      return 'apple-badge-neutral'
  }
}

async function loadPlatformData() {
  loading.value = true
  try {
    const [{ data: tenantData }, { data: userData }] = await Promise.all([
      http.get('/tenants'),
      http.get('/users'),
    ])
    tenants.value = Array.isArray(tenantData) ? tenantData : []
    users.value = Array.isArray(userData) ? userData : []
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '平台数据加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(loadPlatformData)
</script>
