<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <button @click="router.back()" class="p-2 rounded-full hover:bg-secondary transition-colors">
        <ArrowLeftIcon class="w-5 h-5" />
      </button>
      <div>
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wider">AI 增强</p>
        <h2 class="text-3xl font-bold tracking-tight">全方位证伪验证</h2>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left: Action & Progress -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bento-card bg-[#FF3B30] text-white">
          <h3 class="text-xl font-bold mb-4">启动证伪验证</h3>
          <p class="text-white/80 text-sm leading-relaxed mb-8">
            AI 将针对案件中的关键事实进行多维度证伪，识别潜在的虚假陈述、逻辑矛盾及证据瑕疵。
          </p>
          <button
            @click="handleStartFalsification"
            :disabled="loading"
            class="w-full py-3 bg-white text-[#FF3B30] rounded-xl font-bold shadow-lg hover:bg-white/90 transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Loader2Icon v-if="loading" class="w-5 h-5 animate-spin" />
            <span v-else>启动验证</span>
          </button>
        </div>

        <transition name="fade">
          <div v-if="currentTask" class="bento-card border-rose-100 bg-rose-50/10">
            <div class="flex items-center gap-3 mb-6">
              <Loader2Icon
                v-if="['pending', 'processing', 'queued', 'running'].includes(currentTask.status)"
                class="w-5 h-5 animate-spin text-rose-600"
              />
              <CheckCircle2Icon
                v-else-if="['completed', 'success'].includes(currentTask.status)"
                class="w-5 h-5 text-emerald-600"
              />
              <AlertCircleIcon v-else class="w-5 h-5 text-rose-600" />
              <h3 class="font-semibold">验证进度</h3>
            </div>
            <task-progress
              :task-id="currentTask.task_id"
              @completed="handleFalsificationCompleted"
              @retried="handleTaskRetried"
            />
          </div>
        </transition>

        <!-- Summary Stats -->
        <div v-if="falsificationRecords.length > 0" class="grid grid-cols-1 gap-4">
          <div class="bento-card !p-4 flex items-center justify-between">
            <span class="text-sm font-medium text-muted-foreground">总验证项</span>
            <span class="text-2xl font-bold">{{ falsificationSummary.total }}</span>
          </div>
          <div class="bento-card !p-4 flex items-center justify-between border-rose-100 bg-rose-50/30">
            <span class="text-sm font-medium text-rose-600">疑似虚假</span>
            <span class="text-2xl font-bold text-rose-600">{{ falsificationSummary.falsified }}</span>
          </div>
          <div class="bento-card !p-4 flex items-center justify-between border-amber-100 bg-amber-50/30">
            <span class="text-sm font-medium text-amber-600">严重风险</span>
            <span class="text-2xl font-bold text-amber-600">{{ falsificationSummary.critical }}</span>
          </div>
        </div>
      </div>

      <!-- Right: Records -->
      <div class="lg:col-span-2 space-y-6">
        <div v-if="falsificationRecords.length > 0" class="space-y-4">
          <div
            v-for="record in falsificationRecords"
            :key="record.id"
            class="bento-card group transition-all hover:border-primary/30"
          >
            <div class="flex items-start justify-between mb-4">
              <div class="flex items-center gap-2">
                <span
                  class="apple-badge"
                  :class="record.is_falsified ? 'apple-badge-danger' : 'apple-badge-success'"
                >
                  {{ record.is_falsified ? '疑似虚假' : '验证通过' }}
                </span>
                <span
                  class="apple-badge"
                  :class="getSeverityClass(record.severity)"
                >
                  {{ getSeverityText(record.severity) }}
                </span>
              </div>
              <span class="text-[10px] text-muted-foreground font-mono">{{ record.created_at }}</span>
            </div>

            <div class="space-y-4">
              <div class="p-4 rounded-xl bg-secondary/30 border border-border">
                <p class="text-xs font-bold text-muted-foreground uppercase mb-1">验证事实</p>
                <p class="text-sm leading-relaxed">{{ record.fact_description }}</p>
              </div>

              <div v-if="record.is_falsified" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="p-4 rounded-xl bg-rose-50/50 border border-rose-100">
                  <p class="text-xs font-bold text-rose-600 uppercase mb-1">证伪理由</p>
                  <p class="text-sm leading-relaxed text-rose-900">{{ record.reason }}</p>
                </div>
                <div v-if="record.evidence_gap" class="p-4 rounded-xl bg-amber-50/50 border border-amber-100">
                  <p class="text-xs font-bold text-amber-600 uppercase mb-1">证据缺失</p>
                  <p class="text-sm leading-relaxed text-amber-900">{{ record.evidence_gap }}</p>
                </div>
              </div>
            </div>

            <div class="mt-6 pt-4 border-t border-border flex justify-end">
              <button @click="handleViewDetails(record)" class="text-xs font-bold text-primary hover:underline flex items-center gap-1">
                查看详细分析报告 <ChevronRightIcon class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="bento-card flex flex-col items-center justify-center py-32 text-center">
          <div class="w-20 h-20 bg-secondary/50 rounded-full flex items-center justify-center mb-6">
            <ShieldAlertIcon class="w-10 h-10 text-muted-foreground" />
          </div>
          <h3 class="text-xl font-bold">尚未进行证伪验证</h3>
          <p class="text-muted-foreground mt-2">点击左侧按钮启动 AI 全方位证伪验证</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { extractFriendlyError } from '@/lib/formMessages'
import {
  ArrowLeftIcon,
  Loader2Icon,
  ShieldAlertIcon,
  ChevronRightIcon,
  CheckCircle2Icon,
  AlertCircleIcon
} from 'lucide-vue-next'
import { useAIStore } from '@/stores/ai'
import TaskProgress from '@/components/ai/TaskProgress.vue'

defineOptions({
  name: 'FalsificationView',
})

const route = useRoute()
const router = useRouter()
const aiStore = useAIStore()

const caseId = ref(parseInt(route.params.id))
const loading = ref(false)

const currentTask = computed(() => aiStore.currentTask)
const falsificationRecords = computed(() => aiStore.falsificationRecords)
const falsificationSummary = computed(() => aiStore.falsificationSummary)

onMounted(async () => {
  try {
    await aiStore.fetchFalsificationResults(caseId.value)
  } catch (err) {
    ElMessage.error(extractFriendlyError(err, '加载证伪结果失败'))
  }
})

const handleStartFalsification = async () => {
  loading.value = true
  try {
    if (!aiStore.analysisResults.length) {
      await aiStore.fetchAnalysisResults(caseId.value)
    }
    const analysisId = aiStore.analysisResults[0]?.id
    if (!analysisId) {
      ElMessage.warning('请先完成法律分析')
      return
    }
    const task = await aiStore.startFalsification(caseId.value, analysisId)
    aiStore.currentTask = task
    ElMessage.success('证伪验证任务已启动')
  } catch (err) {
    ElMessage.error(extractFriendlyError(err, '启动验证失败'))
  } finally {
    loading.value = false
  }
}

const getSeverityText = (severity) => {
  const map = { critical: '严重风险', major: '高风险', minor: '中低风险' }
  return map[severity] || severity
}

const getSeverityClass = (severity) => {
  switch (severity) {
    case 'major': return 'apple-badge-warning'
    case 'minor': return 'apple-badge-primary'
    case 'critical': return 'apple-badge-danger'
    default: return 'apple-badge-neutral'
  }
}

const handleFalsificationCompleted = async () => {
  ElMessage.success('证伪任务已完成')
  await aiStore.fetchFalsificationResults(caseId.value)
}

const handleTaskRetried = (task) => {
  aiStore.currentTask = task
}

const handleViewDetails = (_record) => {
  ElMessage.info('详细报告功能开发中...')
}
</script>
