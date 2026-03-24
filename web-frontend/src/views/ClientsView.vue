<template>
  <div class="space-y-6">
    <section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Clients</p>
        <h2 class="mt-2 text-3xl font-bold tracking-tight text-slate-900">当事人管理</h2>
        <p class="mt-2 text-sm text-slate-500">
          独立查看当事人资料、最后上传时间、关联案件，并支持直接编辑基础信息。
        </p>
      </div>

      <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
        <el-input
          v-model="filters.q"
          clearable
          placeholder="搜索姓名或手机号"
          @keyup.enter="loadClients"
          @clear="loadClients"
        />
        <el-select v-model="filters.sortBy" @change="loadClients">
          <el-option label="按创建时间" value="created_at" />
          <el-option label="按姓名" value="real_name" />
          <el-option label="按手机号" value="phone" />
          <el-option label="按案件数量" value="case_count" />
          <el-option label="按最后上传时间" value="last_uploaded_at" />
        </el-select>
        <div class="flex gap-3">
          <el-select v-model="filters.sortOrder" class="!w-32" @change="loadClients">
            <el-option label="倒序" value="desc" />
            <el-option label="正序" value="asc" />
          </el-select>
          <button
            @click="loadClients"
            :disabled="loadingList"
            class="inline-flex items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-50"
          >
            刷新
          </button>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <section class="bento-card !p-0 overflow-hidden border border-slate-200/80 bg-white">
        <el-table
          v-loading="loadingList"
          :data="clients"
          empty-text="暂无当事人数据"
          @row-click="openClient"
        >
          <el-table-column label="当事人" min-width="180">
            <template #default="{ row }">
              <div class="space-y-1">
                <p class="font-semibold text-slate-900">{{ row.real_name }}</p>
                <p class="text-xs text-slate-500">{{ row.phone }}</p>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="案件数量" width="110" align="center">
            <template #default="{ row }">
              <span class="apple-badge apple-badge-neutral">{{ row.case_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="150">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="最后上传时间" min-width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.last_uploaded_at, '暂无上传') }}
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="bento-card border border-slate-200/80 bg-white">
        <template v-if="detail">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Client Profile</p>
              <h3 class="mt-2 text-2xl font-bold text-slate-900">{{ detail.real_name }}</h3>
              <p class="mt-2 text-sm text-slate-500">查看资料、编辑基础信息，并从这里进入关联案件详情。</p>
            </div>
            <button
              @click="resetDetail"
              class="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
            >
              返回列表
            </button>
          </div>

          <div class="mt-6 grid gap-4 md:grid-cols-2">
            <div class="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-4">
              <p class="text-xs uppercase tracking-[0.18em] text-slate-400">创建时间</p>
              <p class="mt-2 text-base font-semibold text-slate-900">{{ formatDateTime(detail.created_at) }}</p>
            </div>
            <div class="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-4">
              <p class="text-xs uppercase tracking-[0.18em] text-slate-400">最后上传时间</p>
              <p class="mt-2 text-base font-semibold text-slate-900">{{ formatDateTime(detail.last_uploaded_at, '暂无上传') }}</p>
            </div>
          </div>

          <div class="mt-6 grid gap-4 md:grid-cols-2">
            <label class="space-y-2">
              <span class="text-sm font-medium text-slate-700">姓名</span>
              <el-input v-model="editForm.real_name" maxlength="100" />
            </label>
            <label class="space-y-2">
              <span class="text-sm font-medium text-slate-700">手机号</span>
              <el-input v-model="editForm.phone" maxlength="11" />
            </label>
          </div>

          <div class="mt-4 flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-4">
            <div>
              <p class="text-xs uppercase tracking-[0.18em] text-slate-400">关联案件</p>
              <p class="mt-2 text-base font-semibold text-slate-900">{{ detail.case_count }} 个</p>
            </div>
            <button
              @click="saveClient"
              :disabled="saving"
              class="inline-flex items-center justify-center rounded-xl bg-cyan-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-cyan-700 disabled:opacity-50"
            >
              保存资料
            </button>
          </div>

          <div class="mt-6">
            <div class="flex items-center justify-between">
              <h4 class="text-lg font-semibold text-slate-900">关联案件</h4>
              <span class="text-xs text-slate-500">点击进入案件详情</span>
            </div>
            <div class="mt-4 space-y-3">
              <button
                v-for="item in detail.cases"
                :key="item.id"
                @click="openCase(item.id)"
                class="flex w-full items-start justify-between rounded-2xl border border-slate-200 bg-white px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-cyan-300 hover:shadow-md"
              >
                <div class="space-y-2">
                  <p class="text-sm font-semibold text-slate-900">{{ item.title }}</p>
                  <p class="text-xs text-slate-500">{{ item.case_number }} · {{ formatLegalType(item.legal_type) }}</p>
                  <p class="text-xs text-slate-500">
                    负责律师：{{ item.assigned_lawyer_name || '未分配' }} · 更新于 {{ formatDateTime(item.updated_at) }}
                  </p>
                </div>
                <span class="apple-badge" :class="caseStatusClass(item.status)">
                  {{ formatCaseStatus(item.status) }}
                </span>
              </button>
            </div>
          </div>
        </template>

        <el-empty v-else description="请选择左侧一位当事人" :image-size="84" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'

import { formatCaseStatus, formatLegalType } from '../lib/displayText'
import { extractFriendlyError, validateName, validatePhone } from '../lib/formMessages'
import http from '../lib/http'

const route = useRoute()
const router = useRouter()

const loadingList = ref(false)
const loadingDetail = ref(false)
const saving = ref(false)
const clients = ref([])
const detail = ref(null)

const filters = reactive({
  q: '',
  sortBy: 'created_at',
  sortOrder: 'desc',
})

const editForm = reactive({
  real_name: '',
  phone: '',
})

function formatDateTime(value, fallback = '-') {
  if (!value) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleString('zh-CN', { hour12: false })
}

function caseStatusClass(status) {
  if (status === 'done') return 'apple-badge-success'
  if (status === 'processing') return 'apple-badge-warning'
  return 'apple-badge-primary'
}

async function loadClients() {
  loadingList.value = true
  try {
    const params = {
      sort_by: filters.sortBy,
      sort_order: filters.sortOrder,
    }
    if (filters.q.trim()) {
      params.q = filters.q.trim()
    }
    const { data } = await http.get('/clients', { params })
    clients.value = Array.isArray(data) ? data : []
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '当事人列表加载失败'))
  } finally {
    loadingList.value = false
  }
}

async function loadDetail(id) {
  if (!id) {
    detail.value = null
    editForm.real_name = ''
    editForm.phone = ''
    return
  }

  loadingDetail.value = true
  try {
    const { data } = await http.get(`/clients/${id}`)
    detail.value = data
    editForm.real_name = data.real_name || ''
    editForm.phone = data.phone || ''
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '当事人详情加载失败'))
    detail.value = null
  } finally {
    loadingDetail.value = false
  }
}

function openClient(row) {
  router.push({ name: 'client-detail', params: { id: row.id } })
}

function resetDetail() {
  router.push({ name: 'clients' })
}

function openCase(caseId) {
  router.push({
    name: 'case-detail',
    params: { id: caseId },
    query: {
      from: 'client',
      client_id: String(detail.value.id),
    },
  })
}

async function saveClient() {
  const nameError = validateName(editForm.real_name, '当事人姓名')
  if (nameError) {
    ElMessage.warning(nameError)
    return
  }
  const phoneError = validatePhone(editForm.phone, '当事人手机号')
  if (phoneError) {
    ElMessage.warning(phoneError)
    return
  }
  if (!detail.value?.id) {
    return
  }

  saving.value = true
  try {
    await http.patch(`/clients/${detail.value.id}`, {
      real_name: editForm.real_name.trim(),
      phone: editForm.phone.trim(),
    })
    ElMessage.success('当事人资料已更新')
    await Promise.all([loadClients(), loadDetail(detail.value.id)])
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '当事人资料更新失败'))
  } finally {
    saving.value = false
  }
}

watch(
  () => route.params.id,
  (clientId) => {
    loadDetail(clientId)
  },
  { immediate: true },
)

onMounted(loadClients)
</script>
