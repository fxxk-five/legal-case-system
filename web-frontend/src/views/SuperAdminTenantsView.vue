<template>
  <div class="space-y-6">
    <section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Tenant Operations</p>
        <h2 class="mt-2 text-3xl font-bold tracking-tight text-slate-900">租户管理</h2>
        <p class="mt-2 text-sm text-slate-500">
          统一查看租户状态、租户编码和 AI 月预算，并从这里完成新租户开户。
        </p>
      </div>

      <div class="flex flex-wrap gap-3">
        <button class="apple-btn-secondary" @click="openCreateDialog('organization')">
          新建机构租户
        </button>
        <button class="apple-btn-secondary" @click="openCreateDialog('personal')">
          新建个人租户
        </button>
        <button class="apple-btn-primary" :disabled="loading" @click="loadTenants">
          刷新列表
        </button>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">租户总数</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.total }}</h3>
        <p class="mt-4 text-xs text-slate-500">当前已纳入超管视图的全部租户。</p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">正常租户</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.active }}</h3>
        <p class="mt-4 text-xs text-slate-500">可正常登录和继续处理案件。</p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">停用 / 归档</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.disabled + summary.archived }}</h3>
        <p class="mt-4 text-xs text-slate-500">
          停用 {{ summary.disabled }} 个，归档 {{ summary.archived }} 个。
        </p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">个人空间</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.personal }}</h3>
        <p class="mt-4 text-xs text-slate-500">机构空间 {{ summary.organization }} 个。</p>
      </article>
    </section>

    <section class="bento-card border border-slate-200/80 bg-white">
      <div class="grid grid-cols-1 gap-3 lg:grid-cols-[1.4fr_0.8fr_0.8fr]">
        <el-input
          v-model="filters.keyword"
          clearable
          placeholder="搜索租户名称、编码或 ID"
        />
        <el-select v-model="filters.type" clearable placeholder="全部类型">
          <el-option label="机构空间" value="organization" />
          <el-option label="个人空间" value="personal" />
        </el-select>
        <el-select v-model="filters.status" clearable placeholder="全部状态">
          <el-option label="已创建" value="0" />
          <el-option label="正常" value="1" />
          <el-option label="已停用" value="2" />
          <el-option label="已归档" value="3" />
        </el-select>
      </div>

      <div class="mt-6 overflow-hidden rounded-3xl border border-slate-200">
        <el-table v-loading="loading" :data="filteredTenants" empty-text="暂无租户数据">
          <el-table-column label="租户" min-width="220">
            <template #default="{ row }">
              <div class="space-y-1 py-1">
                <p class="font-semibold text-slate-900">{{ row.name }}</p>
                <p class="text-xs text-slate-500">租户 ID #{{ row.id }}</p>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="编码" min-width="170">
            <template #default="{ row }">
              <code class="rounded-lg bg-slate-100 px-2 py-1 text-xs text-slate-700">
                {{ row.tenant_code }}
              </code>
            </template>
          </el-table-column>

          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              {{ formatTenantType(row.type) }}
            </template>
          </el-table-column>

          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <span class="apple-badge" :class="tenantStatusClass(row.status)">
                {{ formatTenantStatus(row.status) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="AI 月预算" min-width="210">
            <template #default="{ row }">
              <template v-if="budgetCache[row.id]">
                <div class="space-y-1 py-1">
                  <p class="text-sm text-slate-900">
                    {{ formatBudgetLimit(budgetCache[row.id].ai_monthly_budget_limit) }}
                  </p>
                  <p class="text-xs text-slate-500">
                    降级模型：{{ budgetCache[row.id].ai_budget_degrade_model || '未设置' }}
                  </p>
                </div>
              </template>
              <span v-else class="text-sm text-slate-400">点击“预算设置”加载</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="280" fixed="right">
            <template #default="{ row }">
              <div class="flex flex-wrap gap-2 py-1">
                <button
                  class="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                  @click.stop="openBudgetDialog(row)"
                >
                  预算设置
                </button>
                <button
                  v-for="action in statusActions(row.status)"
                  :key="action.status"
                  class="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                  @click.stop="changeTenantStatus(row, action.status)"
                >
                  {{ action.label }}
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog v-model="createDialogVisible" width="720px" title="新建租户">
      <div class="space-y-5">
        <div class="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
          <p class="text-sm font-medium text-slate-900">开户模式</p>
          <p class="mt-1 text-xs text-slate-500">
            后端会返回该租户管理员的启动 token，但超管控制台不会接管登录态，只用于开户初始化。
          </p>
          <el-radio-group v-model="createDialogMode" class="mt-4">
            <el-radio-button label="organization">机构空间</el-radio-button>
            <el-radio-button label="personal">个人空间</el-radio-button>
          </el-radio-group>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">
              {{ createDialogMode === 'organization' ? '机构名称' : '工作空间名称' }}
            </span>
            <el-input
              v-model="createForm.name"
              maxlength="100"
              :placeholder="createDialogMode === 'organization' ? '请输入机构名称' : '请输入工作空间名称'"
            />
          </label>

          <label v-if="createDialogMode === 'organization'" class="space-y-2">
            <span class="text-sm font-medium text-slate-700">联系人</span>
            <el-input v-model="createForm.contact_name" maxlength="100" placeholder="请输入联系人姓名" />
          </label>

          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">管理员姓名</span>
            <el-input v-model="createForm.admin_real_name" maxlength="100" placeholder="请输入管理员姓名" />
          </label>

          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">管理员手机号</span>
            <el-input v-model="createForm.admin_phone" maxlength="11" placeholder="请输入管理员手机号" />
          </label>

          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">管理员密码</span>
            <el-input
              v-model="createForm.admin_password"
              type="password"
              show-password
              maxlength="128"
              placeholder="至少 8 位，且包含字母与数字"
            />
          </label>

          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700">租户编码（可选）</span>
            <el-input v-model="createForm.tenant_code" maxlength="50" placeholder="例如 law-firm-a" />
          </label>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <button
            class="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:bg-slate-50"
            @click="createDialogVisible = false"
          >
            取消
          </button>
          <button class="apple-btn-primary" :disabled="createSubmitting" @click="submitCreateTenant">
            创建租户
          </button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="budgetDialogVisible" width="560px" title="租户 AI 预算">
      <div v-if="budgetTenant" class="space-y-5">
        <div class="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
          <p class="font-medium text-slate-900">{{ budgetTenant.name }}</p>
          <p class="mt-1 text-xs text-slate-500">
            租户 ID #{{ budgetTenant.id }} · {{ budgetTenant.tenant_code }} · {{ formatTenantType(budgetTenant.type) }}
          </p>
        </div>

        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700">月预算上限（元）</span>
          <el-input
            v-model="budgetForm.ai_monthly_budget_limit"
            placeholder="留空表示不限制"
            :disabled="budgetLoading"
          />
        </label>

        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700">超预算降级模型</span>
          <el-input
            v-model="budgetForm.ai_budget_degrade_model"
            maxlength="100"
            placeholder="例如 gpt-4o-mini，留空表示不设置"
            :disabled="budgetLoading"
          />
        </label>
      </div>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <button
            class="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:bg-slate-50"
            @click="budgetDialogVisible = false"
          >
            取消
          </button>
          <button class="apple-btn-primary" :disabled="budgetLoading || budgetSaving" @click="submitBudget">
            保存预算
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'

import { formatTenantStatus, formatTenantType } from '../lib/displayText'
import {
  extractFriendlyError,
  validateName,
  validatePassword,
  validatePhone,
  validateTenantCode,
  validateWorkspaceName,
} from '../lib/formMessages'
import http from '../lib/http'

const loading = ref(false)
const tenants = ref([])

const filters = reactive({
  keyword: '',
  type: '',
  status: '',
})

const budgetCache = reactive({})

const createDialogVisible = ref(false)
const createDialogMode = ref('organization')
const createSubmitting = ref(false)
const createForm = reactive({
  name: '',
  contact_name: '',
  admin_real_name: '',
  admin_phone: '',
  admin_password: '',
  tenant_code: '',
})

const budgetDialogVisible = ref(false)
const budgetLoading = ref(false)
const budgetSaving = ref(false)
const budgetTenant = ref(null)
const budgetForm = reactive({
  ai_monthly_budget_limit: '',
  ai_budget_degrade_model: '',
})

const filteredTenants = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()

  return [...tenants.value]
    .sort((left, right) => Number(right.id) - Number(left.id))
    .filter((tenant) => {
      if (filters.type && tenant.type !== filters.type) {
        return false
      }
      if (filters.status !== '' && String(tenant.status) !== filters.status) {
        return false
      }
      if (!keyword) {
        return true
      }

      return [
        tenant.name,
        tenant.tenant_code,
        String(tenant.id),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    })
})

const summary = computed(() => ({
  total: tenants.value.length,
  active: tenants.value.filter((item) => Number(item.status) === 1).length,
  disabled: tenants.value.filter((item) => Number(item.status) === 2).length,
  archived: tenants.value.filter((item) => Number(item.status) === 3).length,
  organization: tenants.value.filter((item) => item.type === 'organization').length,
  personal: tenants.value.filter((item) => item.type === 'personal').length,
}))

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

function formatBudgetLimit(value) {
  if (value === null || value === undefined || value === '') {
    return '未设置预算'
  }
  return `¥${Number(value).toFixed(2)} / 月`
}

function statusActions(currentStatus) {
  switch (Number(currentStatus)) {
    case 0:
      return [{ status: 1, label: '启用' }]
    case 1:
      return [
        { status: 2, label: '停用' },
        { status: 3, label: '归档' },
      ]
    case 2:
      return [
        { status: 1, label: '启用' },
        { status: 3, label: '归档' },
      ]
    default:
      return []
  }
}

function resetCreateForm() {
  createForm.name = ''
  createForm.contact_name = ''
  createForm.admin_real_name = ''
  createForm.admin_phone = ''
  createForm.admin_password = ''
  createForm.tenant_code = ''
}

function openCreateDialog(mode) {
  createDialogMode.value = mode
  resetCreateForm()
  createDialogVisible.value = true
}

async function loadTenants() {
  loading.value = true
  try {
    const { data } = await http.get('/tenants')
    tenants.value = Array.isArray(data) ? data : []
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '租户列表加载失败'))
  } finally {
    loading.value = false
  }
}

async function changeTenantStatus(row, targetStatus) {
  const nextStatusLabel = formatTenantStatus(targetStatus)
  const confirmed = window.confirm(`确认将租户“${row.name}”调整为“${nextStatusLabel}”吗？`)
  if (!confirmed) {
    return
  }

  try {
    const { data } = await http.patch(`/tenants/${row.id}/status`, { status: targetStatus })
    tenants.value = tenants.value.map((item) => (item.id === row.id ? data : item))
    ElMessage.success(`租户状态已更新为“${nextStatusLabel}”`)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '租户状态更新失败'))
  }
}

async function submitCreateTenant() {
  const nameValidator =
    createDialogMode.value === 'organization'
      ? validateWorkspaceName(createForm.name, '机构名称')
      : validateWorkspaceName(createForm.name, '工作空间名称')
  if (nameValidator) {
    ElMessage.warning(nameValidator)
    return
  }

  if (createDialogMode.value === 'organization') {
    const contactError = validateName(createForm.contact_name, '联系人')
    if (contactError) {
      ElMessage.warning(contactError)
      return
    }
  }

  const adminNameError = validateName(createForm.admin_real_name, '管理员姓名')
  if (adminNameError) {
    ElMessage.warning(adminNameError)
    return
  }

  const phoneError = validatePhone(createForm.admin_phone, '管理员手机号')
  if (phoneError) {
    ElMessage.warning(phoneError)
    return
  }

  const passwordError = validatePassword(createForm.admin_password, '管理员密码')
  if (passwordError) {
    ElMessage.warning(passwordError)
    return
  }

  const tenantCodeError = validateTenantCode(createForm.tenant_code, { required: false })
  if (tenantCodeError) {
    ElMessage.warning(tenantCodeError)
    return
  }

  createSubmitting.value = true
  try {
    const payload =
      createDialogMode.value === 'organization'
        ? {
            name: createForm.name.trim(),
            contact_name: createForm.contact_name.trim(),
            admin_real_name: createForm.admin_real_name.trim(),
            admin_phone: createForm.admin_phone.trim(),
            admin_password: createForm.admin_password,
            tenant_code: createForm.tenant_code.trim() || null,
          }
        : {
            workspace_name: createForm.name.trim(),
            admin_real_name: createForm.admin_real_name.trim(),
            admin_phone: createForm.admin_phone.trim(),
            admin_password: createForm.admin_password,
            tenant_code: createForm.tenant_code.trim() || null,
          }

    const endpoint = createDialogMode.value === 'organization' ? '/tenants/organization' : '/tenants/personal'
    const { data } = await http.post(endpoint, payload)
    createDialogVisible.value = false
    resetCreateForm()
    await loadTenants()
    ElMessage.success(`租户“${data?.tenant?.name || payload.name || payload.workspace_name}”创建成功`)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '租户创建失败'))
  } finally {
    createSubmitting.value = false
  }
}

async function openBudgetDialog(row) {
  budgetTenant.value = row
  budgetDialogVisible.value = true
  budgetLoading.value = true
  budgetForm.ai_monthly_budget_limit = ''
  budgetForm.ai_budget_degrade_model = ''

  try {
    const { data } = await http.get(`/tenants/${row.id}/ai-budget`)
    budgetCache[row.id] = data
    budgetForm.ai_monthly_budget_limit =
      data?.ai_monthly_budget_limit === null || data?.ai_monthly_budget_limit === undefined
        ? ''
        : String(data.ai_monthly_budget_limit)
    budgetForm.ai_budget_degrade_model = data?.ai_budget_degrade_model || ''
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '预算信息加载失败'))
    budgetDialogVisible.value = false
  } finally {
    budgetLoading.value = false
  }
}

async function submitBudget() {
  if (!budgetTenant.value) {
    return
  }

  const limitText = budgetForm.ai_monthly_budget_limit.trim()
  const modelName = budgetForm.ai_budget_degrade_model.trim()

  let parsedLimit = null
  if (limitText) {
    parsedLimit = Number(limitText)
    if (!Number.isFinite(parsedLimit) || parsedLimit < 0) {
      ElMessage.warning('月预算上限必须是大于等于 0 的数字。')
      return
    }
  }

  budgetSaving.value = true
  try {
    const { data } = await http.patch(`/tenants/${budgetTenant.value.id}/ai-budget`, {
      ai_monthly_budget_limit: parsedLimit,
      ai_budget_degrade_model: modelName || null,
      clear_monthly_budget_limit: !limitText,
      clear_budget_degrade_model: !modelName,
    })
    budgetCache[budgetTenant.value.id] = data
    budgetDialogVisible.value = false
    ElMessage.success('租户预算已更新')
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '租户预算更新失败'))
  } finally {
    budgetSaving.value = false
  }
}

onMounted(loadTenants)
</script>
