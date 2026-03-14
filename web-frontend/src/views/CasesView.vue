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

    <el-table :data="cases" stripe>
      <el-table-column label="案号" min-width="160">
        <template #default="{ row }">
          <RouterLink :to="`/cases/${row.id}`" class="case-link">{{ row.case_number }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column label="当事人" min-width="140">
        <template #default="{ row }">
          {{ row.client?.real_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建案件" width="520px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="案号">
          <el-input v-model="form.case_number" placeholder="例如 CASE-2026-001" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入案件标题" />
        </el-form-item>
        <el-form-item label="当事人姓名">
          <el-input v-model="form.client_real_name" placeholder="请输入当事人姓名" />
        </el-form-item>
        <el-form-item label="当事人手机号">
          <el-input v-model="form.client_phone" placeholder="请输入手机号" />
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
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { RouterLink } from 'vue-router'

import http from '../lib/http'

const cases = ref([])
const dialogVisible = ref(false)
const statusFilter = ref('')
const submitting = ref(false)

const form = reactive({
  case_number: '',
  title: '',
  client_phone: '',
  client_real_name: '',
})

async function loadCases() {
  const params = {}
  if (statusFilter.value) {
    params.status = statusFilter.value
  }
  const { data } = await http.get('/cases', { params })
  cases.value = data
}

function resetForm() {
  form.case_number = ''
  form.title = ''
  form.client_phone = ''
  form.client_real_name = ''
}

async function handleCreateCase() {
  submitting.value = true
  try {
    await http.post('/cases', form)
    ElMessage.success('案件创建成功')
    dialogVisible.value = false
    resetForm()
    await loadCases()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '案件创建失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadCases)
</script>
