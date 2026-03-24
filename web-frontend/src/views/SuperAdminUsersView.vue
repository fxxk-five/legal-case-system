<template>
  <div class="space-y-6">
    <section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-slate-400">Global Users</p>
        <h2 class="mt-2 text-3xl font-bold tracking-tight text-slate-900">用户总览</h2>
        <p class="mt-2 text-sm text-slate-500">
          超级管理员从平台视角查看账号结构、跨租户手机号复用和当前身份治理边界。
        </p>
      </div>

      <button class="apple-btn-primary" :disabled="loading" @click="loadData">
        刷新数据
      </button>
    </section>

    <section class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">账号总数</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.total }}</h3>
        <p class="mt-4 text-xs text-slate-500">已纳入平台级审计视图的全部用户。</p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">状态分布</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.active }}</h3>
        <p class="mt-4 text-xs text-slate-500">
          正常 {{ summary.active }}，待审批 {{ summary.pending }}，停用 {{ summary.disabled }}。
        </p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">角色结构</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ summary.lawyers }}</h3>
        <p class="mt-4 text-xs text-slate-500">
          律师 {{ summary.lawyers }}，当事人 {{ summary.clients }}，机构管理员 {{ summary.tenantAdmins }}。
        </p>
      </article>

      <article class="bento-card border border-slate-200/80 bg-white">
        <p class="text-sm text-slate-500">跨租户重复手机号</p>
        <h3 class="mt-3 text-4xl font-bold text-slate-900">{{ duplicatePhoneGroups.length }}</h3>
        <p class="mt-4 text-xs text-slate-500">
          这类账号登录时必须依赖租户编码、扫码票据或案件邀请上下文。
        </p>
      </article>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <article class="bento-card border border-slate-200/80 bg-white">
        <div class="grid grid-cols-1 gap-3 lg:grid-cols-[1.35fr_0.7fr_0.7fr_0.95fr]">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索姓名、手机号、用户 ID"
          />
          <el-select v-model="filters.role" clearable placeholder="全部角色">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="机构管理员" value="tenant_admin" />
            <el-option label="律师" value="lawyer" />
            <el-option label="当事人" value="client" />
          </el-select>
          <el-select v-model="filters.status" clearable placeholder="全部状态">
            <el-option label="待审批" value="0" />
            <el-option label="正常" value="1" />
            <el-option label="已停用" value="2" />
            <el-option label="已拒绝" value="3" />
          </el-select>
          <el-select v-model="filters.tenantId" clearable filterable placeholder="全部租户">
            <el-option
              v-for="tenant in tenantOptions"
              :key="tenant.value"
              :label="tenant.label"
              :value="tenant.value"
            />
          </el-select>
        </div>

        <div class="mt-6 overflow-hidden rounded-3xl border border-slate-200">
          <el-table v-loading="loading" :data="filteredUsers" empty-text="暂无用户数据">
            <el-table-column label="用户" min-width="220">
              <template #default="{ row }">
                <div class="space-y-1 py-1">
                  <p class="font-semibold text-slate-900">{{ row.real_name || '未命名账号' }}</p>
                  <p class="text-xs text-slate-500">{{ row.phone }}</p>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="角色" width="130">
              <template #default="{ row }">
                {{ formatRole(row.role) }}
              </template>
            </el-table-column>

            <el-table-column label="租户" min-width="180">
              <template #default="{ row }">
                <div class="space-y-1 py-1">
                  <p class="text-sm text-slate-900">{{ resolveTenantName(row.tenant_id) }}</p>
                  <p class="text-xs text-slate-500">租户 #{{ row.tenant_id }}</p>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <span class="apple-badge" :class="userStatusClass(row.status)">
                  {{ formatUserStatus(row.status) }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="管理标记" width="140">
              <template #default="{ row }">
                <span class="apple-badge" :class="row.is_tenant_admin ? 'apple-badge-primary' : 'apple-badge-neutral'">
                  {{ row.is_tenant_admin ? '租户管理员' : '普通成员' }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="用户 ID" width="110">
              <template #default="{ row }">
                <span class="text-sm text-slate-600">#{{ row.id }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </article>

      <div class="space-y-6">
        <article class="bento-card border border-slate-200/80 bg-white">
          <h3 class="text-lg font-semibold text-slate-900">身份治理说明</h3>
          <div class="mt-5 space-y-4">
            <div
              v-for="item in governanceRules"
              :key="item.title"
              class="rounded-2xl border border-slate-200 bg-slate-50/70 p-4"
            >
              <div class="font-medium text-slate-900">{{ item.title }}</div>
              <p class="mt-1 text-sm text-slate-500">{{ item.description }}</p>
            </div>
          </div>
        </article>

        <article class="bento-card border border-slate-200/80 bg-white">
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="text-lg font-semibold text-slate-900">重复手机号样本</h3>
              <p class="mt-1 text-sm text-slate-500">用于辅助判断是否需要 tenant_code 或邀请上下文。</p>
            </div>
            <span class="apple-badge apple-badge-warning">{{ duplicatePhoneGroups.length }} 组</span>
          </div>

          <div class="mt-5 space-y-3">
            <div
              v-for="group in duplicatePhoneGroups.slice(0, 6)"
              :key="group.phone"
              class="rounded-2xl border border-slate-200 bg-slate-50/70 p-4"
            >
              <p class="font-medium text-slate-900">{{ group.phone }}</p>
              <p class="mt-1 text-sm text-slate-500">
                命中 {{ group.tenantIds.length }} 个租户：
                {{ group.tenantIds.map((tenantId) => resolveTenantName(tenantId)).join('、') }}
              </p>
            </div>
            <div v-if="!duplicatePhoneGroups.length" class="text-sm text-slate-500">
              当前没有跨租户重复手机号样本。
            </div>
          </div>
        </article>

        <article class="bento-card border border-slate-200/80 bg-white">
          <h3 class="text-lg font-semibold text-slate-900">当前能力边界</h3>
          <p class="mt-3 text-sm leading-7 text-slate-500">
            当前后端已开放超级管理员全局用户读取接口，但尚未开放超管直接修改用户状态、角色或手机号的接口。
            因此本页现阶段是“审计 + 排查”控制台，不是“直接改账号”的后台。
          </p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'

import { formatRole, formatUserStatus } from '../lib/displayText'
import { extractFriendlyError } from '../lib/formMessages'
import http from '../lib/http'

const loading = ref(false)
const users = ref([])
const tenants = ref([])

const filters = reactive({
  keyword: '',
  role: '',
  status: '',
  tenantId: '',
})

const governanceRules = [
  {
    title: '手机号是登录主标识，但不是平台全局唯一键',
    description:
      '平台的实际唯一性应当是 tenant_id + phone。同一手机号可以在多个租户存在，但不能在同一租户下重复。',
  },
  {
    title: '微信一键登录必须回绑定手机号',
    description:
      '微信只是认证凭证，不是最终账号键。只有拿到手机号并命中租户上下文后，才能确定用户记录。',
  },
  {
    title: '案件邀请只提供绑定上下文',
    description:
      '当事人从小程序邀请进入后，无论走短信验证码、微信一键登录还是账号密码登录，最终都要按手机号归并到同一案件账号。',
  },
]

const summary = computed(() => ({
  total: users.value.length,
  active: users.value.filter((item) => Number(item.status) === 1).length,
  pending: users.value.filter((item) => Number(item.status) === 0).length,
  disabled: users.value.filter((item) => Number(item.status) === 2).length,
  lawyers: users.value.filter((item) => item.role === 'lawyer').length,
  clients: users.value.filter((item) => item.role === 'client').length,
  tenantAdmins: users.value.filter((item) => item.role === 'tenant_admin').length,
}))

const tenantMap = computed(() => {
  return tenants.value.reduce((result, tenant) => {
    result[tenant.id] = tenant
    return result
  }, {})
})

const tenantOptions = computed(() => {
  return [...tenants.value]
    .sort((left, right) => left.name.localeCompare(right.name, 'zh-CN'))
    .map((tenant) => ({
      value: String(tenant.id),
      label: `${tenant.name} (#${tenant.id})`,
    }))
})

const filteredUsers = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()

  return [...users.value]
    .sort((left, right) => Number(right.id) - Number(left.id))
    .filter((user) => {
      if (filters.role && user.role !== filters.role) {
        return false
      }
      if (filters.status !== '' && String(user.status) !== filters.status) {
        return false
      }
      if (filters.tenantId && String(user.tenant_id) !== filters.tenantId) {
        return false
      }
      if (!keyword) {
        return true
      }

      return [
        user.real_name,
        user.phone,
        String(user.id),
        resolveTenantName(user.tenant_id),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    })
})

const duplicatePhoneGroups = computed(() => {
  const groups = new Map()

  for (const user of users.value) {
    const key = user.phone
    if (!groups.has(key)) {
      groups.set(key, { phone: key, tenantIds: new Set() })
    }
    groups.get(key).tenantIds.add(user.tenant_id)
  }

  return [...groups.values()]
    .filter((item) => item.tenantIds.size > 1)
    .map((item) => ({
      phone: item.phone,
      tenantIds: [...item.tenantIds].sort((left, right) => Number(left) - Number(right)),
    }))
    .sort((left, right) => right.tenantIds.length - left.tenantIds.length)
})

function resolveTenantName(tenantId) {
  return tenantMap.value[tenantId]?.name || `未知租户 #${tenantId}`
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

async function loadData() {
  loading.value = true
  try {
    const [{ data: userData }, { data: tenantData }] = await Promise.all([
      http.get('/users'),
      http.get('/tenants'),
    ])
    users.value = Array.isArray(userData) ? userData : []
    tenants.value = Array.isArray(tenantData) ? tenantData : []
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '用户总览加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
