<template>
  <div class="space-y-8">
    <section
      class="rounded-[28px] border border-slate-200/80 bg-[linear-gradient(135deg,rgba(8,47,73,0.98),rgba(17,94,89,0.92),rgba(21,128,61,0.82))] px-6 py-7 text-white shadow-2xl shadow-emerald-100/60"
    >
      <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.24em] text-emerald-100/80">AI Console</p>
          <h2 class="mt-2 text-3xl font-bold tracking-tight">分析管理</h2>
          <p class="mt-3 max-w-2xl text-sm text-emerald-50/90">
            在这里查看 AI 用量、任务状态、提示词和模型源配置，形成可运营、可排障的统一控制台。
          </p>
        </div>
        <button
          @click="loadAll"
          :disabled="loadingPage"
          class="inline-flex items-center justify-center rounded-xl border border-white/15 bg-white/10 px-4 py-2.5 text-sm font-medium text-white backdrop-blur-sm transition hover:bg-white/15 disabled:opacity-50"
        >
          刷新控制台
        </button>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-6 md:grid-cols-3">
      <article v-for="card in usageCards" :key="card.key" class="bento-card border border-slate-200/80 bg-white">
        <p class="text-xs uppercase tracking-[0.2em] text-slate-400">{{ card.label }}</p>
        <h3 class="mt-3 text-4xl font-bold tracking-tight text-slate-900">{{ card.value }}</h3>
        <p class="mt-3 text-sm text-slate-500">{{ card.description }}</p>
        <div class="mt-5 flex items-center justify-between text-xs text-slate-500">
          <span>Token: {{ card.tokens }}</span>
          <span>成本: {{ card.cost }}</span>
        </div>
      </article>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_0.85fr]">
      <article class="bento-card border border-slate-200/80 bg-white">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Task Mix</p>
          <h3 class="mt-2 text-2xl font-bold text-slate-900">任务与状态分布</h3>
        </div>

        <div class="mt-6 grid gap-6 lg:grid-cols-2">
          <div>
            <p class="text-sm font-semibold text-slate-800">按功能</p>
            <div class="mt-4 space-y-3">
              <div v-for="item in usage.task_type_breakdown" :key="item.key" class="space-y-2">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-slate-700">{{ item.label }}</span>
                  <span class="font-semibold text-slate-900">{{ item.count }}</span>
                </div>
                <div class="h-2 rounded-full bg-slate-100">
                  <div class="h-2 rounded-full bg-cyan-500" :style="{ width: `${percentage(item.count, maxTaskTypeCount)}%` }" />
                </div>
              </div>
              <el-empty v-if="!usage.task_type_breakdown.length" description="暂无任务类型统计" :image-size="60" />
            </div>
          </div>

          <div>
            <p class="text-sm font-semibold text-slate-800">按状态</p>
            <div class="mt-4 space-y-3">
              <div v-for="item in usage.status_breakdown" :key="item.key" class="space-y-2">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-slate-700">{{ item.label }}</span>
                  <span class="font-semibold text-slate-900">{{ item.count }}</span>
                </div>
                <div class="h-2 rounded-full bg-slate-100">
                  <div class="h-2 rounded-full bg-emerald-500" :style="{ width: `${percentage(item.count, maxStatusCount)}%` }" />
                </div>
              </div>
              <el-empty v-if="!usage.status_breakdown.length" description="暂无状态统计" :image-size="60" />
            </div>
          </div>
        </div>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Models</p>
        <h3 class="mt-2 text-2xl font-bold text-slate-900">模型使用分布</h3>
        <div class="mt-6 space-y-3">
          <div
            v-for="item in usage.model_breakdown"
            :key="item.model"
            class="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-4"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="text-sm font-semibold text-slate-900">{{ item.model }}</p>
              <span class="text-xs text-slate-500">{{ item.result_count }} 次结果</span>
            </div>
            <div class="mt-3 flex items-center justify-between text-sm text-slate-600">
              <span>Token {{ item.token_usage }}</span>
              <span>成本 {{ formatCost(item.cost_total) }}</span>
            </div>
          </div>
          <el-empty v-if="!usage.model_breakdown.length" description="暂无模型统计数据" :image-size="72" />
        </div>
      </article>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <article class="bento-card border border-slate-200/80 bg-white">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Provider</p>
            <h3 class="mt-2 text-2xl font-bold text-slate-900">模型源设置</h3>
          </div>
          <span class="apple-badge" :class="provider.locked ? 'apple-badge-warning' : 'apple-badge-success'">
            {{ provider.locked ? '已锁定' : '可编辑' }}
          </span>
        </div>

        <div class="mt-6 grid gap-4">
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">Provider 类型</span>
            <el-select v-model="providerForm.provider_type" :disabled="!provider.editable">
              <el-option label="OpenAI 兼容" value="openai_compatible" />
              <el-option label="Official Cloud" value="official_cloud" />
            </el-select>
          </label>
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">Base URL</span>
            <el-input v-model="providerForm.base_url" :disabled="!provider.editable" placeholder="https://api.example.com/v1" />
          </label>
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">模型名</span>
            <el-input v-model="providerForm.model" :disabled="!provider.editable" placeholder="gpt-4o-mini" />
          </label>
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">API Key</span>
            <el-input
              v-model="providerForm.api_key"
              :disabled="!provider.editable"
              placeholder="留空则保持当前密钥"
              show-password
            />
            <p class="text-xs text-slate-500">当前已保存：{{ provider.api_key_masked || '未设置' }}</p>
          </label>
        </div>

        <div class="mt-6 flex justify-end">
          <button
            @click="saveProvider"
            :disabled="savingProvider || !provider.editable"
            class="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:opacity-50"
          >
            保存模型源
          </button>
        </div>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Prompts</p>
          <h3 class="mt-2 text-2xl font-bold text-slate-900">提示词管理</h3>
        </div>

        <div class="mt-6 grid gap-4">
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">解析提示词</span>
            <el-input v-model="promptForm.parse_prompt" type="textarea" :rows="4" maxlength="20000" show-word-limit />
          </label>
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">分析提示词</span>
            <el-input v-model="promptForm.analyze_prompt" type="textarea" :rows="4" maxlength="20000" show-word-limit />
          </label>
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">证伪提示词</span>
            <el-input v-model="promptForm.falsify_prompt" type="textarea" :rows="4" maxlength="20000" show-word-limit />
          </label>
        </div>

        <div class="mt-6 flex justify-end">
          <button
            @click="savePrompts"
            :disabled="savingPrompts"
            class="inline-flex items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-50"
          >
            保存提示词
          </button>
        </div>
      </article>
    </section>

    <section class="bento-card border border-slate-200/80 bg-white">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Tasks</p>
          <h3 class="mt-2 text-2xl font-bold text-slate-900">AI 任务列表</h3>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <el-select v-model="filters.task_type" clearable placeholder="任务类型" class="!w-40" @change="reloadTasks">
            <el-option label="文档解析" value="parse" />
            <el-option label="法律分析" value="analyze" />
            <el-option label="证伪核验" value="falsify" />
          </el-select>
          <el-select v-model="filters.status" clearable placeholder="任务状态" class="!w-40" @change="reloadTasks">
            <el-option label="排队中" value="queued" />
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="重试中" value="retrying" />
            <el-option label="死信" value="dead" />
          </el-select>
          <button
            @click="loadTasks"
            class="inline-flex items-center justify-center rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            刷新任务
          </button>
        </div>
      </div>

      <div class="mt-6">
        <el-table v-loading="aiStore.loading" :data="aiStore.taskList" empty-text="暂无 AI 任务">
          <el-table-column prop="task_id" label="任务 ID" min-width="220" />
          <el-table-column prop="case_id" label="案件 ID" width="100" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              {{ formatTaskType(row.task_type) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <span class="apple-badge" :class="statusBadgeClass(row.status)">{{ formatTaskStatus(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="进度" min-width="160">
            <template #default="{ row }">
              <el-progress :percentage="Number(row.progress || 0)" :stroke-width="8" />
            </template>
          </el-table-column>
          <el-table-column label="更新时间" min-width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <button
                v-if="row.status === 'failed'"
                @click="retryTask(row)"
                :disabled="retryingTaskId === row.task_id"
                class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
              >
                重试
              </button>
              <span v-else class="text-xs text-slate-400">-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'

import { extractFriendlyError } from '../lib/formMessages'
import http from '../lib/http'
import { useAIStore } from '../stores/ai'

const aiStore = useAIStore()
const loadingPage = ref(false)
const savingPrompts = ref(false)
const savingProvider = ref(false)
const retryingTaskId = ref('')

const usage = reactive({
  day: { task_count: 0, token_usage: 0, cost_total: 0 },
  week: { task_count: 0, token_usage: 0, cost_total: 0 },
  month: { task_count: 0, token_usage: 0, cost_total: 0 },
  task_type_breakdown: [],
  status_breakdown: [],
  model_breakdown: [],
})

const promptForm = reactive({
  parse_prompt: '',
  analyze_prompt: '',
  falsify_prompt: '',
})

const provider = reactive({
  provider_type: 'openai_compatible',
  base_url: '',
  model: '',
  api_key_masked: '',
  editable: true,
  locked: false,
})

const providerForm = reactive({
  provider_type: 'openai_compatible',
  base_url: '',
  model: '',
  api_key: '',
})

const filters = reactive({
  status: '',
  task_type: '',
})

const usageCards = computed(() => [
  {
    key: 'day',
    label: '最近 24 小时',
    value: usage.day.task_count,
    description: '过去一天内创建的 AI 任务数量。',
    tokens: usage.day.token_usage,
    cost: formatCost(usage.day.cost_total),
  },
  {
    key: 'week',
    label: '最近 7 天',
    value: usage.week.task_count,
    description: '观察一周内 AI 功能整体调用热度。',
    tokens: usage.week.token_usage,
    cost: formatCost(usage.week.cost_total),
  },
  {
    key: 'month',
    label: '最近 30 天',
    value: usage.month.task_count,
    description: '观察租户月度使用趋势和成本消耗。',
    tokens: usage.month.token_usage,
    cost: formatCost(usage.month.cost_total),
  },
])

const maxTaskTypeCount = computed(() =>
  Math.max(1, ...usage.task_type_breakdown.map((item) => Number(item.count || 0))),
)

const maxStatusCount = computed(() =>
  Math.max(1, ...usage.status_breakdown.map((item) => Number(item.count || 0))),
)

function percentage(value, total) {
  if (!total) return 0
  return Math.min(100, Math.round((Number(value || 0) / Number(total)) * 100))
}

function formatCost(value) {
  return `¥${Number(value || 0).toFixed(4)}`
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatTaskType(value) {
  if (value === 'parse') return '文档解析'
  if (value === 'analyze') return '法律分析'
  if (value === 'falsify') return '证伪核验'
  return value || '-'
}

function formatTaskStatus(value) {
  if (value === 'queued') return '排队中'
  if (value === 'pending') return '待处理'
  if (value === 'processing') return '处理中'
  if (value === 'completed') return '已完成'
  if (value === 'failed') return '失败'
  if (value === 'retrying') return '重试中'
  if (value === 'dead') return '死信'
  return value || '-'
}

function statusBadgeClass(status) {
  if (status === 'failed' || status === 'dead') return 'apple-badge-danger'
  if (status === 'completed') return 'apple-badge-success'
  if (status === 'processing' || status === 'retrying') return 'apple-badge-warning'
  return 'apple-badge-primary'
}

async function loadUsage() {
  const { data } = await http.get('/analytics/ai-usage')
  Object.assign(usage.day, data.day || {})
  Object.assign(usage.week, data.week || {})
  Object.assign(usage.month, data.month || {})
  usage.task_type_breakdown = Array.isArray(data.task_type_breakdown) ? data.task_type_breakdown : []
  usage.status_breakdown = Array.isArray(data.status_breakdown) ? data.status_breakdown : []
  usage.model_breakdown = Array.isArray(data.model_breakdown) ? data.model_breakdown : []
}

async function loadPrompts() {
  const { data } = await http.get('/analytics/prompts')
  promptForm.parse_prompt = data.parse_prompt || ''
  promptForm.analyze_prompt = data.analyze_prompt || ''
  promptForm.falsify_prompt = data.falsify_prompt || ''
}

async function loadProvider() {
  const { data } = await http.get('/analytics/provider-settings')
  provider.provider_type = data.provider_type || 'openai_compatible'
  provider.base_url = data.base_url || ''
  provider.model = data.model || ''
  provider.api_key_masked = data.api_key_masked || ''
  provider.editable = Boolean(data.editable)
  provider.locked = Boolean(data.locked)

  providerForm.provider_type = provider.provider_type
  providerForm.base_url = provider.base_url
  providerForm.model = provider.model
  providerForm.api_key = ''
}

async function loadTasks() {
  try {
    await aiStore.fetchTaskList({
      page: 1,
      page_size: 20,
      status: filters.status || undefined,
      task_type: filters.task_type || undefined,
    })
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '任务列表加载失败'))
  }
}

async function loadAll() {
  loadingPage.value = true
  try {
    await Promise.all([loadUsage(), loadPrompts(), loadProvider(), loadTasks()])
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '分析管理数据加载失败'))
  } finally {
    loadingPage.value = false
  }
}

async function savePrompts() {
  savingPrompts.value = true
  try {
    await http.put('/analytics/prompts', { ...promptForm })
    ElMessage.success('提示词已保存')
    await loadPrompts()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '提示词保存失败'))
  } finally {
    savingPrompts.value = false
  }
}

async function saveProvider() {
  savingProvider.value = true
  try {
    await http.put('/analytics/provider-settings', { ...providerForm })
    ElMessage.success('模型源设置已保存')
    await loadProvider()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '模型源设置保存失败'))
  } finally {
    savingProvider.value = false
  }
}

async function retryTask(task) {
  retryingTaskId.value = task.task_id
  try {
    await aiStore.retryTask(task.task_id, 'manual retry from analysis console')
    ElMessage.success('已发起任务重试')
    await loadTasks()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '任务重试失败'))
  } finally {
    retryingTaskId.value = ''
  }
}

function reloadTasks() {
  loadTasks()
}

onMounted(loadAll)
</script>
