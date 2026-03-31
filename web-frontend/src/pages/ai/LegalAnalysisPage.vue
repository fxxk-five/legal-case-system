<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <button @click="router.back()" class="p-2 rounded-full hover:bg-secondary transition-colors">
        <ArrowLeftIcon class="w-5 h-5" />
      </button>
      <div>
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wider">AI 增强</p>
        <h2 class="text-3xl font-bold tracking-tight">法律深度分析</h2>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left: Action & Progress -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bento-card bg-[#007AFF] text-white">
          <h3 class="text-xl font-bold mb-4">启动智能分析</h3>
          <p class="text-white/80 text-sm leading-relaxed mb-8">
            基于已提取的案件事实，AI 将为您生成深度法律分析报告，包括胜诉率预估、强弱点分析及法律建议。
          </p>
          <button
            @click="handleStartAnalysis"
            :disabled="loading"
            class="w-full py-3 bg-white text-[#007AFF] rounded-xl font-bold shadow-lg hover:bg-white/90 transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Loader2Icon v-if="loading" class="w-5 h-5 animate-spin" />
            <span v-else>开始分析</span>
          </button>
        </div>

        <transition name="fade">
          <div v-if="currentTask" class="bento-card border-primary/20 bg-primary/[0.02]">
            <div class="flex items-center gap-3 mb-6">
              <Loader2Icon
                v-if="['pending', 'processing', 'queued', 'running'].includes(currentTask.status)"
                class="w-5 h-5 animate-spin text-primary"
              />
              <CheckCircle2Icon
                v-else-if="['completed', 'success'].includes(currentTask.status)"
                class="w-5 h-5 text-emerald-600"
              />
              <AlertCircleIcon v-else class="w-5 h-5 text-rose-600" />
              <h3 class="font-semibold">分析进度</h3>
            </div>
            <task-progress
              :task-id="currentTask.task_id"
              @completed="handleAnalysisCompleted"
              @retried="handleTaskRetried"
            />
          </div>
        </transition>
      </div>

      <!-- Right: Results -->
      <div class="lg:col-span-2 space-y-6">
        <div v-if="latestAnalysis" class="space-y-6">
          <!-- Summary Row -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bento-card flex flex-col items-center justify-center text-center">
              <p class="readonly-label mb-4">胜诉率预估</p>
              <el-progress
                type="dashboard"
                :percentage="latestAnalysis.win_rate * 100"
                :color="colors"
                :stroke-width="10"
                :width="120"
              />
            </div>
            <div class="bento-card md:col-span-2">
              <p class="text-sm font-medium text-muted-foreground mb-2">分析摘要</p>
              <p class="text-sm leading-relaxed text-foreground/80">
                {{ latestAnalysis.summary }}
              </p>
            </div>
          </div>

          <!-- Detailed Tabs -->
          <div class="bento-card !p-0 overflow-hidden">
            <el-tabs v-model="activeTab" class="apple-tabs px-6 pt-2">
              <el-tab-pane label="强弱点分析" name="swot">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 py-6">
                  <div class="space-y-4">
                    <div class="flex items-center gap-2 text-emerald-600">
                      <PlusCircleIcon class="w-5 h-5" />
                      <h4 class="font-bold">优势 (Strengths)</h4>
                    </div>
                    <ul class="space-y-3">
                      <li v-for="(item, index) in latestAnalysis.strengths" :key="index" class="text-sm flex gap-3">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0"></span>
                        {{ item }}
                      </li>
                    </ul>
                  </div>
                  <div class="space-y-4">
                    <div class="flex items-center gap-2 text-rose-600">
                      <MinusCircleIcon class="w-5 h-5" />
                      <h4 class="font-bold">劣势 (Weaknesses)</h4>
                    </div>
                    <ul class="space-y-3">
                      <li v-for="(item, index) in latestAnalysis.weaknesses" :key="index" class="text-sm flex gap-3">
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1.5 shrink-0"></span>
                        {{ item }}
                      </li>
                    </ul>
                  </div>
                </div>
              </el-tab-pane>
              <el-tab-pane label="法律建议" name="advice">
                <div class="py-6 space-y-4">
                  <div v-for="(item, index) in latestAnalysis.recommendations" :key="index" class="p-4 rounded-2xl bg-secondary/30 border border-border flex gap-4">
                    <div class="p-2 bg-primary/5 rounded-lg text-primary shrink-0 h-fit">
                      <LightbulbIcon class="w-4 h-4" />
                    </div>
                    <p class="text-sm leading-relaxed">{{ item }}</p>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="bento-card flex flex-col items-center justify-center py-32 text-center">
          <div class="w-20 h-20 bg-secondary/50 rounded-full flex items-center justify-center mb-6">
            <BrainIcon class="w-10 h-10 text-muted-foreground" />
          </div>
          <h3 class="text-xl font-bold">尚未生成分析报告</h3>
          <p class="text-muted-foreground mt-2">点击左侧按钮启动 AI 法律深度分析</p>
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
  BrainIcon,
  PlusCircleIcon,
  MinusCircleIcon,
  LightbulbIcon,
  CheckCircle2Icon,
  AlertCircleIcon
} from 'lucide-vue-next'
import { useAIStore } from '@/stores/ai'
import TaskProgress from '@/components/ai/TaskProgress.vue'

const route = useRoute()
const router = useRouter()
const aiStore = useAIStore()

const caseId = ref(parseInt(route.params.id))
const activeTab = ref('swot')
const loading = ref(false)

const currentTask = computed(() => aiStore.currentTask)
const latestAnalysis = computed(() => aiStore.latestAnalysis)

const colors = [
  { color: '#FF3B30', percentage: 20 },
  { color: '#FF9500', percentage: 40 },
  { color: '#34C759', percentage: 60 },
  { color: '#007AFF', percentage: 80 },
  { color: '#5856D6', percentage: 100 },
]

onMounted(async () => {
  try {
    await aiStore.fetchAnalysisResults(caseId.value)
  } catch (err) {
    ElMessage.error(extractFriendlyError(err, '加载分析结果失败'))
  }
})

const handleStartAnalysis = async () => {
  loading.value = true
  try {
    const task = await aiStore.startAnalysis(caseId.value)
    aiStore.currentTask = task
    ElMessage.success('分析任务已启动')
  } catch (err) {
    ElMessage.error(extractFriendlyError(err, '启动分析失败'))
  } finally {
    loading.value = false
  }
}

const handleAnalysisCompleted = async () => {
  ElMessage.success('分析任务已完成')
  await aiStore.fetchAnalysisResults(caseId.value)
}

const handleTaskRetried = (task) => {
  aiStore.currentTask = task
}
</script>
