<template>
  <div class="max-w-4xl mx-auto space-y-8">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">机构设置</h2>
        <p class="text-muted-foreground">管理您的律所或个人工作空间信息</p>
      </div>
      <button
        @click="loadTenant"
        class="p-2 rounded-xl hover:bg-secondary transition-colors"
      >
        <RefreshCwIcon class="w-5 h-5 text-muted-foreground" />
      </button>
    </div>

    <div v-if="tenant" class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <!-- Sidebar Info -->
      <div class="md:col-span-1 space-y-6">
        <div class="bento-card flex flex-col items-center text-center py-10">
          <div class="w-20 h-20 bg-primary/5 rounded-3xl flex items-center justify-center mb-4">
            <BuildingIcon class="w-10 h-10 text-primary" />
          </div>
          <h3 class="text-xl font-bold">{{ tenant.name }}</h3>
          <p class="text-sm text-muted-foreground mt-1">{{ formatTenantType(tenant.type) }}</p>

          <div class="mt-6 w-full pt-6 border-t border-border space-y-3">
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">机构编码</span>
              <span class="font-mono font-medium">{{ tenant.tenant_code }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">当前状态</span>
              <span class="text-emerald-600 font-medium">{{ formatTenantStatus(tenant.status) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Form -->
      <div class="md:col-span-2">
        <div class="bento-card space-y-6">
          <h3 class="text-lg font-semibold">基本信息</h3>

          <el-form :model="tenantForm" layout="vertical" class="space-y-6">
            <div class="space-y-2">
              <label class="text-sm font-medium">机构名称</label>
              <el-input v-model="tenantForm.name" placeholder="请输入机构名称" class="apple-input" />
              <p class="text-xs text-muted-foreground">机构名称最多 100 个字符，建议与正式名称保持一致。</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <label class="text-sm font-medium">机构编码 (不可修改)</label>
                <el-input :model-value="tenant.tenant_code" disabled class="apple-input opacity-60" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium">机构类型</label>
                <el-input :model-value="formatTenantType(tenant.type)" disabled class="apple-input opacity-60" />
              </div>
            </div>

            <div class="pt-4 border-t border-border flex justify-end">
              <button
                @click="saveTenant"
                :disabled="submitting"
                class="inline-flex items-center px-6 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium shadow-apple hover:opacity-90 transition-all active:scale-95 disabled:opacity-50"
              >
                <SaveIcon v-if="!submitting" class="w-4 h-4 mr-2" />
                <Loader2Icon v-else class="w-4 h-4 mr-2 animate-spin" />
                保存修改
              </button>
            </div>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import {
  BuildingIcon,
  RefreshCwIcon,
  SaveIcon,
  Loader2Icon
} from 'lucide-vue-next'

import { formatTenantStatus, formatTenantType } from '../lib/displayText'
import http from '../lib/http'
import { extractFriendlyError, validateWorkspaceName } from '../lib/formMessages'

const tenant = ref(null)
const tenantForm = reactive({
  name: '',
})
const submitting = ref(false)

async function loadTenant() {
  try {
    const { data } = await http.get('/tenants/current')
    tenant.value = data
    tenantForm.name = data.name
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '机构信息加载失败'))
  }
}

async function saveTenant() {
  const validationMessage = validateWorkspaceName(tenantForm.name, '机构名称')
  if (validationMessage) {
    ElMessage.warning(validationMessage)
    return
  }

  submitting.value = true
  try {
    const { data } = await http.patch('/tenants/current', { name: tenantForm.name })
    tenant.value = data
    ElMessage.success('机构信息已更新')
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '保存失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(loadTenant)
</script>
