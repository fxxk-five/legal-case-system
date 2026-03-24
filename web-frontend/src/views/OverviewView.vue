<template>
  <div class="space-y-8">
    <section class="rounded-[28px] border border-slate-200/80 bg-[linear-gradient(135deg,rgba(15,23,42,0.96),rgba(30,41,59,0.92),rgba(14,116,144,0.78))] px-6 py-7 text-white shadow-2xl shadow-slate-200/70">
      <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div class="space-y-3">
          <p class="text-xs uppercase tracking-[0.28em] text-cyan-100/80">Workspace Overview</p>
          <h2 class="text-3xl font-bold tracking-tight">概览</h2>
          <p class="max-w-2xl text-sm text-slate-200">
            当前登录用户、机构状态和上次登录后的关键变化都汇总在这里，避免遗漏新增案件、材料和待审批成员。
          </p>
        </div>
        <div class="grid gap-3 text-sm sm:grid-cols-2">
          <div class="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 backdrop-blur-sm">
            <p class="text-xs uppercase tracking-[0.2em] text-cyan-100/70">当前用户</p>
            <p class="mt-2 text-base font-semibold">{{ formatText(authStore.currentUser?.real_name) }}</p>
            <p class="mt-1 text-slate-200">{{ formatRole(authStore.currentUser?.role) }}</p>
          </div>
          <div class="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 backdrop-blur-sm">
            <p class="text-xs uppercase tracking-[0.2em] text-cyan-100/70">机构</p>
            <p class="mt-2 text-base font-semibold">{{ formatText(tenant?.name) }}</p>
            <p class="mt-1 text-slate-200">{{ formatTenantType(tenant?.type) }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
      <article
        v-for="card in summaryCards"
        :key="card.key"
        class="bento-card relative overflow-hidden border border-slate-200/80 bg-white"
      >
        <div :class="card.glowClass" class="absolute right-0 top-0 h-24 w-24 rounded-full blur-3xl opacity-80" />
        <div class="relative flex items-start justify-between">
          <div>
            <p class="text-sm font-medium text-slate-500">{{ card.label }}</p>
            <h3 class="mt-3 text-4xl font-bold tracking-tight text-slate-900">{{ card.value }}</h3>
          </div>
          <div :class="card.iconClass" class="rounded-2xl p-3">
            <component :is="card.icon" class="h-5 w-5" />
          </div>
        </div>
        <p class="relative mt-5 text-sm text-slate-500">{{ card.description }}</p>
      </article>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_1fr]">
      <article class="bento-card border border-slate-200/80 bg-white">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Since Last Login</p>
            <h3 class="mt-2 text-2xl font-bold text-slate-900">关键动态提醒</h3>
            <p class="mt-2 text-sm text-slate-500">
              {{ baselineDescription }}
            </p>
          </div>
          <div class="rounded-2xl bg-cyan-50 p-3 text-cyan-700">
            <SparklesIcon class="h-5 w-5" />
          </div>
        </div>

        <div
          v-if="stats.has_login_baseline"
          class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
        >
          <div
            v-for="item in deltaCards"
            :key="item.key"
            class="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-4"
          >
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">{{ item.label }}</p>
            <div class="mt-3 flex items-end gap-2">
              <span class="text-3xl font-bold text-slate-900">{{ item.value }}</span>
              <span class="mb-1 text-xs text-slate-500">{{ item.unit }}</span>
            </div>
            <p class="mt-3 text-sm text-slate-500">{{ item.description }}</p>
          </div>
        </div>

        <div
          v-else
          class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center"
        >
          <p class="text-base font-semibold text-slate-900">首次登录基线已建立</p>
          <p class="mt-2 text-sm text-slate-500">
            下次登录后，这里会展示新增案件、材料上传和待审批成员变化。
          </p>
        </div>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Identity</p>
            <h3 class="mt-2 text-2xl font-bold text-slate-900">当前登录信息</h3>
          </div>
          <div class="rounded-2xl bg-slate-100 p-3 text-slate-700">
            <BadgeInfoIcon class="h-5 w-5" />
          </div>
        </div>

        <div class="mt-6 space-y-4">
          <div v-for="item in userCards" :key="item.label" class="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-4">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">{{ item.label }}</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">{{ item.value }}</p>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import {
  BadgeInfoIcon,
  BriefcaseIcon,
  Clock3Icon,
  ShieldAlertIcon,
  SparklesIcon,
  UsersIcon,
} from 'lucide-vue-next'

import { extractFriendlyError } from '../lib/formMessages'
import { formatRole, formatTenantType, formatText } from '../lib/displayText'
import http from '../lib/http'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const tenant = ref(null)
const stats = reactive({
  lawyer_count: 0,
  client_total: 0,
  case_total: 0,
  case_in_progress: 0,
  case_closed: 0,
  pending_member_count: 0,
  can_view_pending_members: false,
  has_login_baseline: false,
  delta_since: null,
  delta_case_count: 0,
  delta_file_count: 0,
  delta_file_case_count: 0,
  delta_deadline_risk_count: 0,
  delta_pending_member_count: 0,
})

function normalizeStats(payload = {}) {
  stats.lawyer_count = Number(payload.lawyer_count ?? 0)
  stats.client_total = Number(payload.client_total ?? 0)
  stats.case_total = Number(payload.case_total ?? payload.case_count ?? 0)
  stats.case_in_progress = Number(payload.case_in_progress ?? 0)
  stats.case_closed = Number(payload.case_closed ?? 0)
  stats.pending_member_count = Number(payload.pending_member_count ?? payload.pending_lawyer_count ?? 0)
  stats.can_view_pending_members = Boolean(payload.can_view_pending_members)
  stats.has_login_baseline = Boolean(payload.has_login_baseline)
  stats.delta_since = payload.delta_since ?? null
  stats.delta_case_count = Number(payload.delta_case_count ?? 0)
  stats.delta_file_count = Number(payload.delta_file_count ?? 0)
  stats.delta_file_case_count = Number(payload.delta_file_case_count ?? 0)
  stats.delta_deadline_risk_count = Number(payload.delta_deadline_risk_count ?? 0)
  stats.delta_pending_member_count = Number(payload.delta_pending_member_count ?? 0)
}

function formatDateTime(value) {
  if (!value) return '首次登录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '首次登录'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const summaryCards = computed(() => {
  const cards = [
    {
      key: 'case_total',
      label: '案件总数',
      value: stats.case_total,
      description: '当前账号可见范围内的全部案件。',
      icon: BriefcaseIcon,
      iconClass: 'bg-slate-900 text-white',
      glowClass: 'bg-slate-200',
    },
    {
      key: 'client_total',
      label: '当事人总数',
      value: stats.client_total,
      description: '当前租户已归档的当事人数量。',
      icon: UsersIcon,
      iconClass: 'bg-cyan-100 text-cyan-700',
      glowClass: 'bg-cyan-100',
    },
    {
      key: 'case_in_progress',
      label: '进行中案件',
      value: stats.case_in_progress,
      description: '未完结案件总量，便于优先处理。',
      icon: Clock3Icon,
      iconClass: 'bg-amber-100 text-amber-700',
      glowClass: 'bg-amber-100',
    },
  ]

  if (stats.can_view_pending_members) {
    cards.push({
      key: 'pending_member_count',
      label: '待审批律师',
      value: stats.pending_member_count,
      description: '等待机构管理员审批的成员申请。',
      icon: ShieldAlertIcon,
      iconClass: 'bg-rose-100 text-rose-700',
      glowClass: 'bg-rose-100',
    })
  } else {
    cards.push({
      key: 'lawyer_count',
      label: '律师账号数',
      value: stats.lawyer_count,
      description: '当前机构已启用的律师与管理员账号。',
      icon: ShieldAlertIcon,
      iconClass: 'bg-emerald-100 text-emerald-700',
      glowClass: 'bg-emerald-100',
    })
  }

  return cards
})

const deltaCards = computed(() => [
  {
    key: 'delta_case_count',
    label: '新增案件',
    value: stats.delta_case_count,
    unit: '个',
    description: '自上次登录后新建并进入你可见范围的案件。',
  },
  {
    key: 'delta_file_count',
    label: '新增材料',
    value: stats.delta_file_count,
    unit: '份',
    description: `涉及 ${stats.delta_file_case_count} 个案件的新上传材料。`,
  },
  {
    key: 'delta_deadline_risk_count',
    label: '临期案件',
    value: stats.delta_deadline_risk_count,
    unit: '个',
    description: '30 天内到期且仍未完成的案件变动。',
  },
  {
    key: 'delta_pending_member_count',
    label: '新增待审批',
    value: stats.delta_pending_member_count,
    unit: '人',
    description: '上次登录后新增的待审批成员申请。',
  },
])

const userCards = computed(() => [
  { label: '姓名', value: formatText(authStore.currentUser?.real_name) },
  { label: '手机号', value: formatText(authStore.currentUser?.phone) },
  { label: '角色', value: formatRole(authStore.currentUser?.role) },
  { label: '机构编码', value: formatText(tenant.value?.tenant_code, '未分配') },
])

const baselineDescription = computed(() => {
  if (!stats.has_login_baseline) {
    return '本次登录会建立首个统计基线，下一次开始展示“较上次登录变化”。'
  }
  return `统计窗口起点：${formatDateTime(stats.delta_since)}`
})

onMounted(async () => {
  try {
    if (!authStore.currentUser) {
      await authStore.fetchCurrentUser()
    }

    const [tenantResponse, statsResponse] = await Promise.all([
      http.get('/tenants/current'),
      http.get('/stats/dashboard'),
    ])

    tenant.value = tenantResponse.data
    normalizeStats(statsResponse.data)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '概览信息加载失败'))
  }
})
</script>
