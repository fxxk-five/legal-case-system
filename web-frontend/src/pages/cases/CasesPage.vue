<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-3xl font-bold tracking-tight text-foreground">案件中心</h2>
        <p class="text-muted-foreground">管理并追踪所有法律案件的进展</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="dialogVisible = true"
          class="inline-flex items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-apple transition-all hover:bg-primary/90 active:scale-95"
        >
          <PlusIcon class="mr-2 h-4 w-4" />
          新建案件
        </button>
      </div>
    </div>

    <div class="bento-card border-border/50">
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <el-input
          v-model="keyword"
          placeholder="搜索案号或标题"
          clearable
          class="apple-input lg:col-span-2"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <SearchIcon class="w-4 h-4 text-muted-foreground" />
          </template>
        </el-input>

        <el-select
          v-model="statusFilter"
          placeholder="按状态筛选"
          clearable
          class="apple-select"
          @change="handleFilterChange"
        >
          <el-option label="全部状态" value="" />
          <el-option label="新建" value="new" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="done" />
        </el-select>

        <el-select
          v-model="legalTypeFilter"
          placeholder="按法律类型筛选"
          clearable
          class="apple-select"
          @change="handleFilterChange"
        >
          <el-option label="全部类型" value="" />
          <el-option v-for="item in LEGAL_TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>

        <el-select
          v-model="sortValue"
          placeholder="排序方式"
          class="apple-select"
          @change="handleFilterChange"
        >
          <el-option label="创建时间（新→旧）" value="created_at_desc" />
          <el-option label="创建时间（旧→新）" value="created_at_asc" />
          <el-option label="更新时间（新→旧）" value="updated_at_desc" />
          <el-option label="更新时间（旧→新）" value="updated_at_asc" />
          <el-option label="法律类型（A→Z）" value="legal_type_asc" />
          <el-option label="法律类型（Z→A）" value="legal_type_desc" />
          <el-option label="截止时间（近→远）" value="deadline_asc" />
          <el-option label="截止时间（远→近）" value="deadline_desc" />
        </el-select>
      </div>
      <div class="mt-3 flex items-center gap-3">
        <button
          @click="handleSearch"
          class="px-4 py-2 rounded-xl border border-border text-sm font-medium hover:bg-secondary transition-colors"
        >
          查询
        </button>
        <span class="text-xs text-muted-foreground">共 {{ pagination.total }} 条</span>
      </div>
    </div>

    <div class="bento-card !p-0 overflow-hidden border-border/50 shadow-sm">
      <el-table
        v-loading="loading"
        :data="cases"
        empty-text="暂无案件数据"
        class="apple-table"
        header-cell-class-name="apple-table-header"
      >
        <el-table-column label="案号" min-width="160">
          <template #default="{ row }">
            <RouterLink :to="`/cases/${row.id}`" class="font-medium text-primary hover:underline decoration-primary/30 underline-offset-4">
              {{ row.case_number }}
            </RouterLink>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="法律类型" min-width="130">
          <template #default="{ row }">
            <span class="text-muted-foreground text-sm">{{ formatLegalType(row.legal_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="当事人" min-width="140">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-[10px] font-bold">
                {{ row.client?.real_name?.charAt(0) || '?' }}
              </div>
              {{ formatText(row.client?.real_name) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <span
              class="apple-badge"
              :class="statusBadgeClass(row.status)"
            >
              {{ formatCaseStatus(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">
            <span class="text-muted-foreground text-sm">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="170">
          <template #default="{ row }">
            <span class="text-muted-foreground text-sm">{{ formatDateTime(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="截止时间" min-width="170">
          <template #default="{ row }">
            <span class="text-muted-foreground text-sm">{{ formatDateTime(row.deadline) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="临期提醒" min-width="180">
          <template #default="{ row }">
            <span class="apple-badge" :class="reminderBadgeClass(getCaseReminder(row).level)">
              {{ getCaseReminder(row).text }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="flex justify-end">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      title="新建案件"
      width="520px"
      class="apple-dialog"
      :show-close="false"
    >
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">新建案件</h3>
          <button @click="dialogVisible = false" class="p-1 rounded-full hover:bg-secondary transition-colors">
            <XIcon class="w-5 h-5 text-muted-foreground" />
          </button>
        </div>
      </template>

      <div class="space-y-5 py-2">
        <div class="space-y-2">
          <label class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">案号</label>
          <el-input v-model="form.case_number" placeholder="例如 CASE-2026-001" class="apple-input" />
          <p class="text-[12px] text-muted-foreground">可选，不填写将按“租户-年份-法律类型-序号”自动生成。</p>
        </div>

        <div class="space-y-2">
          <label class="text-sm font-medium leading-none">标题</label>
          <el-input v-model="form.title" placeholder="请输入案件标题" class="apple-input" />
          <p class="text-[12px] text-muted-foreground">请输入案件名称或摘要，最多 255 个字符。</p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">法律类型</label>
            <el-select v-model="form.legal_type" placeholder="请选择法律类型" class="apple-select w-full">
              <el-option v-for="item in LEGAL_TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">截止时间</label>
            <el-date-picker
              v-model="form.deadline"
              type="datetime"
              placeholder="可选"
              class="apple-input w-full"
              clearable
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">当事人姓名</label>
            <el-input v-model="form.client_real_name" placeholder="姓名" class="apple-input" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">当事人手机号</label>
            <el-input v-model="form.client_phone" placeholder="手机号" class="apple-input" />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-end gap-3 pt-4">
          <button
            @click="dialogVisible = false"
            class="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            取消
          </button>
          <button
            @click="handleCreateCase"
            :disabled="submitting"
            class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2 text-sm font-medium text-primary-foreground shadow-apple transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50"
          >
            <Loader2Icon v-if="submitting" class="mr-2 h-4 w-4 animate-spin" />
            创建案件
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { RouterLink } from 'vue-router'
import { PlusIcon, XIcon, Loader2Icon, SearchIcon } from 'lucide-vue-next'

import { formatCaseStatus, formatLegalType, formatText } from '../lib/displayText'
import http from '../lib/http'
import { extractFriendlyError } from '../lib/formMessages'

const LEGAL_TYPE_OPTIONS = [
  { value: 'civil_loan', label: '民间借贷' },
  { value: 'labor_dispute', label: '劳动争议' },
  { value: 'contract_dispute', label: '合同纠纷' },
  { value: 'marriage_family', label: '婚姻家事' },
  { value: 'traffic_accident', label: '交通事故' },
  { value: 'criminal_defense', label: '刑事辩护' },
  { value: 'other', label: '其他' },
]

const cases = ref([])
const dialogVisible = ref(false)
const statusFilter = ref('')
const legalTypeFilter = ref('')
const keyword = ref('')
const sortValue = ref('created_at_desc')
const submitting = ref(false)
const loading = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const form = reactive({
  case_number: '',
  title: '',
  legal_type: '',
  deadline: null,
  client_phone: '',
  client_real_name: '',
})

function statusBadgeClass(status) {
  switch (status) {
    case 'new': return 'apple-badge-primary'
    case 'processing': return 'apple-badge-warning'
    case 'done': return 'apple-badge-success'
    default: return 'apple-badge-neutral'
  }
}

function reminderBadgeClass(level) {
  switch (level) {
    case 'danger': return 'apple-badge-danger'
    case 'warning': return 'apple-badge-warning'
    case 'success': return 'apple-badge-success'
    case 'info': return 'apple-badge-primary'
    default: return 'apple-badge-neutral'
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

function parseSortValue() {
  const raw = sortValue.value || 'created_at_desc'
  const splitIndex = raw.lastIndexOf('_')
  if (splitIndex <= 0) {
    return {
      sort_by: 'created_at',
      sort_order: 'desc',
    }
  }

  return {
    sort_by: raw.slice(0, splitIndex) || 'created_at',
    sort_order: raw.slice(splitIndex + 1) || 'desc',
  }
}

function getCaseReminder(row) {
  if (row.status === 'done') {
    return { level: 'success', text: '已结案' }
  }

  if (row.deadline) {
    const deadline = new Date(row.deadline)
    if (!Number.isNaN(deadline.getTime())) {
      const diffMs = deadline.getTime() - Date.now()
      const diffDays = Math.ceil(diffMs / (24 * 60 * 60 * 1000))

      if (diffDays < 0) {
        return { level: 'danger', text: `已逾期 ${Math.abs(diffDays)} 天` }
      }
      if (diffDays <= 7) {
        return { level: 'danger', text: `${diffDays} 天内到期` }
      }
      if (diffDays <= 30) {
        return { level: 'warning', text: `${diffDays} 天内到期` }
      }
      return { level: 'neutral', text: '进度正常' }
    }
  }

  if (row.status === 'processing') {
    return { level: 'info', text: '处理中，请关注更新' }
  }
  if (row.status === 'new') {
    return { level: 'neutral', text: '新建待推进' }
  }
  return { level: 'neutral', text: '请关注状态' }
}

async function loadCases({ resetPage = false } = {}) {
  if (resetPage) {
    pagination.page = 1
  }

  loading.value = true
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ...parseSortValue(),
  }
  if (statusFilter.value) {
    params.status = statusFilter.value
  }
  if (legalTypeFilter.value) {
    params.legal_type = legalTypeFilter.value
  }
  if (keyword.value.trim()) {
    params.q = keyword.value.trim()
  }

  try {
    const response = await http.get('/cases', { params })
    cases.value = response.data
    pagination.total = Number(response.headers?.['x-total-count'] || 0)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '案件列表加载失败'))
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  loadCases({ resetPage: true })
}

function handleSearch() {
  loadCases({ resetPage: true })
}

function handlePageChange(page) {
  pagination.page = page
  loadCases()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadCases()
}

async function handleCreateCase() {
  if (!form.legal_type) {
    ElMessage.warning('请选择法律类型')
    return
  }
  submitting.value = true
  try {
    await http.post('/cases', form)
    ElMessage.success('案件创建成功')
    dialogVisible.value = false
    await loadCases({ resetPage: true })
    form.case_number = ''
    form.title = ''
    form.legal_type = ''
    form.deadline = null
    form.client_phone = ''
    form.client_real_name = ''
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '创建失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadCases()
})
</script>

<style>
.apple-table {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: transparent;
  @apply !bg-transparent;
}

.apple-table-header {
  @apply !bg-gray-50 !text-gray-400 !font-semibold !text-xs uppercase tracking-wider;
}

.apple-dialog {
  @apply !rounded-3xl !p-6 !shadow-2xl !border-none;
}

.apple-input .el-input__wrapper {
  @apply !rounded-xl !shadow-none !border !border-gray-100 !bg-gray-50/50 focus-within:!ring-2 focus-within:!ring-blue-100 focus-within:!border-[#007AFF] transition-all;
}

.apple-select .el-input__wrapper {
  @apply !rounded-xl !shadow-none !border !border-gray-100 !bg-white hover:!border-[#007AFF] transition-all;
}

.apple-badge-danger {
  @apply bg-red-100 text-red-700;
}
</style>
