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
        <div class="field-tip">机构名称最多 100 个字符，建议与正式名称保持一致。</div>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

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

<style scoped>
.field-tip {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}
</style>
