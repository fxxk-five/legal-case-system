<template>
  <div class="space-y-8">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">管理概览</h2>
        <p class="text-muted-foreground">实时监控机构运行状态与关键指标</p>
      </div>
      <button
        @click="loadStats"
        :disabled="loading"
        class="inline-flex items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-apple transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50"
      >
        <RefreshCwIcon class="mr-2 h-4 w-4" :class="{ 'animate-spin': loading }" />
        刷新数据
      </button>
    </div>

    <!-- Bento Grid Stats -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bento-card group relative overflow-hidden">
        <div class="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
          <UsersIcon class="h-12 w-12" />
        </div>
        <p class="text-sm font-medium text-muted-foreground">律师总数</p>
        <div class="mt-2 flex items-baseline gap-2">
          <h2 class="text-4xl font-bold tracking-tight">{{ stats.lawyer_count }}</h2>
          <span class="text-xs font-medium text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded-full">+2 本月</span>
        </div>
        <p class="mt-4 text-xs text-muted-foreground">当前机构已开通的专业账号</p>
      </div>

      <div class="bento-card group relative overflow-hidden">
        <div class="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
          <BriefcaseIcon class="h-12 w-12" />
        </div>
        <p class="text-sm font-medium text-muted-foreground">案件总数</p>
        <div class="mt-2 flex items-baseline gap-2">
          <h2 class="text-4xl font-bold tracking-tight">{{ stats.case_count }}</h2>
        </div>
        <p class="mt-4 text-xs text-muted-foreground">系统内流转的所有案件记录</p>
      </div>

      <div class="bento-card group relative overflow-hidden border-primary/20 bg-primary/[0.02]">
        <div class="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
          <ShieldAlertIcon class="h-12 w-12" />
        </div>
        <p class="text-sm font-medium text-muted-foreground">待审批律师</p>
        <div class="mt-2 flex items-baseline gap-2">
          <h2 class="text-4xl font-bold tracking-tight text-primary">{{ stats.pending_lawyer_count }}</h2>
        </div>
        <p class="mt-4 text-xs text-muted-foreground">需要您尽快审核的入驻申请</p>
      </div>
    </div>

    <!-- Secondary Bento Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bento-card h-[300px] flex flex-col justify-between">
        <div>
          <h3 class="font-semibold">系统活跃度</h3>
          <p class="text-sm text-muted-foreground">过去 7 天的系统访问趋势</p>
        </div>
        <div class="flex-1 flex items-end gap-2 pt-8">
          <div v-for="i in 7" :key="i"
            class="flex-1 bg-primary/10 rounded-t-lg transition-all hover:bg-primary/30"
            :style="{ height: Math.random() * 100 + '%' }"
          ></div>
        </div>
      </div>

      <div class="bento-card h-[300px]">
        <h3 class="font-semibold mb-4">快捷操作</h3>
        <div class="grid grid-cols-2 gap-4">
          <button class="flex flex-col items-center justify-center p-4 rounded-2xl border border-border hover:bg-secondary transition-colors gap-2">
            <UserPlusIcon class="h-6 w-6 text-primary" />
            <span class="text-sm font-medium">邀请律师</span>
          </button>
          <button class="flex flex-col items-center justify-center p-4 rounded-2xl border border-border hover:bg-secondary transition-colors gap-2">
            <FilePlusIcon class="h-6 w-6 text-primary" />
            <span class="text-sm font-medium">新建案件</span>
          </button>
          <button class="flex flex-col items-center justify-center p-4 rounded-2xl border border-border hover:bg-secondary transition-colors gap-2">
            <Settings2Icon class="h-6 w-6 text-primary" />
            <span class="text-sm font-medium">系统配置</span>
          </button>
          <button class="flex flex-col items-center justify-center p-4 rounded-2xl border border-border hover:bg-secondary transition-colors gap-2">
            <DownloadIcon class="h-6 w-6 text-primary" />
            <span class="text-sm font-medium">导出报表</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import {
  UsersIcon,
  BriefcaseIcon,
  ShieldAlertIcon,
  RefreshCwIcon,
  UserPlusIcon,
  FilePlusIcon,
  Settings2Icon,
  DownloadIcon
} from 'lucide-vue-next'

import http from '../lib/http'
import { extractFriendlyError } from '../lib/formMessages'

const stats = reactive({
  lawyer_count: 0,
  case_count: 0,
  pending_lawyer_count: 0,
})
const loading = ref(false)

async function loadStats() {
  loading.value = true
  try {
    const { data } = await http.get('/stats/dashboard')
    Object.assign(stats, data)
  } catch (error) {
    ElMessage.error(extractFriendlyError(error, '统计数据加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>
