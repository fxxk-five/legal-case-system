<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">案件中心</p>
        <h2>案件列表</h2>
      </div>
      <div class="toolbar">
        <el-select v-model="statusFilter" placeholder="按状态筛选" clearable @change="loadCases">
          <el-option label="全部" value="" />
          <el-option label="新建" value="new" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="done" />
        </el-select>
        <el-button @click="loadCases">刷新</el-button>
        <el-button type="primary" @click="dialogVisible = true">新建案件</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="cases" stripe empty-text="暂无案件数据">
      <el-table-column label="案号" min-width="160">
        <template #default="{ row }">
          <RouterLink :to="`/cases/${row.id}`" class="case-link">{{ row.case_number }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column label="当事人" min-width="140">
        <template #default="{ row }">
          {{ formatText(row.client?.real_name) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          {{ formatCaseStatus(row.status) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建案件" width="520px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="案号">
          <el-input v-model="form.case_number" placeholder="例如 CASE-2026-001" />
          <div class="field-tip">建议使用清晰的案号规则，最多 100 个字符。</div>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入案件标题" />
          <div class="field-tip">请输入案件名称或摘要，最多 255 个字符。</div>
        </el-form-item>
        <el-form-item label="当事人姓名">
          <el-input v-model="form.client_real_name" placeholder="请输入当事人姓名" />
          <div class="field-tip">请输入真实姓名，方便后续归档和联系。</div>
        </el-form-item>
        <el-form-item label="当事人手机号">
          <el-input v-model="form.client_phone" placeholder="请输入手机号" />
          <div class="field-tip">请输入 6 到 20 位数字。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreateCase">创建</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RouterLink } from 'vue-router'

import { formatCaseStatus, formatText } from '../lib/displayText'
import http from '../lib/http'
import { extractFriendlyError, validateName, validatePhone, validateWorkspaceName } from '../lib/formMessages'

const cases = ref([])
const dialogVisible = ref(false)
const statusFilter = ref('')
const submitting = ref(false)
const loading = ref(false)

const form = reactive({
  case_number: '',
  title: '',
  client_phone: '',
  client_real_name: '',
})

async function loadCases() {
  loading.value = true
  const params = {}
  if (statusFilter.value) {
    params.status = statusFilter.value
  }
  try {
    const { data } = await http.get('/cases', { params })
    cases.value = data
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '案件列表加载失败'))
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.case_number = ''
  form.title = ''
  form.client_phone = ''
  form.client_real_name = ''
}

async function handleCreateCase() {
  const validationMessage =
    validateWorkspaceName(form.case_number, '案号') ||
    validateWorkspaceName(form.title, '案件标题') ||
    validateName(form.client_real_name, '当事人姓名') ||
    validatePhone(form.client_phone, '当事人手机号')
  if (validationMessage) {
    ElMessage.warning(validationMessage)
    return
  }

  submitting.value = true
  try {
    await http.post('/cases', form)
    ElMessage.success('案件创建成功')
    dialogVisible.value = false
    resetForm()
    await loadCases()
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '案件创建失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(loadCases)
</script>

<style scoped>
.field-tip {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}
</style>
