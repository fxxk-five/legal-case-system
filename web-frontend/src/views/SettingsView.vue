<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">管理员</p>
        <h2>机构设置</h2>
      </div>
      <el-button @click="loadTenant">刷新</el-button>
    </div>

    <el-form v-if="tenant" :model="tenantForm" label-width="120px" class="settings-form">
      <el-form-item label="机构编码">
        <el-input :model-value="tenant.tenant_code" disabled />
      </el-form-item>
      <el-form-item label="机构名称">
        <el-input v-model="tenantForm.name" />
      </el-form-item>
      <el-form-item label="机构类型">
        <el-input :model-value="tenant.type" disabled />
      </el-form-item>
      <el-form-item label="状态">
        <el-input :model-value="tenant.status" disabled />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="saveTenant">保存修改</el-button>
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

import http from '../lib/http'

const tenant = ref(null)
const tenantForm = reactive({
  name: '',
})
const submitting = ref(false)

async function loadTenant() {
  const { data } = await http.get('/tenants/current')
  tenant.value = data
  tenantForm.name = data.name
}

async function saveTenant() {
  submitting.value = true
  try {
    const { data } = await http.patch('/tenants/current', { name: tenantForm.name })
    tenant.value = data
    ElMessage.success('机构信息已更新')
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadTenant)
</script>
