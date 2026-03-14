<template>
  <section class="cases-page">
    <div class="section-heading">
      <div>
        <p class="header-label">案件中心</p>
        <h2>案件列表</h2>
      </div>
      <el-button type="primary" @click="loadCases">刷新</el-button>
    </div>

    <el-table :data="cases" stripe>
      <el-table-column prop="case_number" label="案号" min-width="160" />
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column label="当事人" min-width="140">
        <template #default="{ row }">
          {{ row.client?.real_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
    </el-table>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import http from '../lib/http'

const cases = ref([])

async function loadCases() {
  const { data } = await http.get('/cases')
  cases.value = data
}

onMounted(loadCases)
</script>
