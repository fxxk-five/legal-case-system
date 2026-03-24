<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <button @click="router.back()" class="p-2 rounded-full hover:bg-secondary transition-colors">
        <ArrowLeftIcon class="w-5 h-5" />
      </button>
      <div>
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wider">AI 增强</p>
        <h2 class="text-3xl font-bold tracking-tight">文档智能解析</h2>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left: Upload & Progress -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bento-card">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-2 bg-blue-50 rounded-xl text-[#007AFF]">
              <FileUpIcon class="w-5 h-5" />
            </div>
            <h3 class="font-bold text-gray-800">上传案件文档</h3>
          </div>
          <file-uploader
            :case-id="caseId"
            @success="handleUploadSuccess"
            @parse="handleStartParse"
          />
        </div>

        <transition name="fade">
          <div v-if="currentTask" class="bento-card border-blue-100 bg-blue-50/10">
            <div class="flex items-center gap-3 mb-6">
              <div class="p-2 bg-blue-50 rounded-xl text-[#007AFF]">
                <Loader2Icon
                  v-if="['pending', 'processing', 'queued', 'running'].includes(currentTask.status)"
                  class="w-5 h-5 animate-spin"
                />
                <CheckCircle2Icon v-else-if="['completed', 'success'].includes(currentTask.status)" class="w-5 h-5 text-green-600" />
                <AlertCircleIcon v-else class="w-5 h-5 text-red-600" />
              </div>
              <h3 class="font-bold text-gray-800">解析进度</h3>
            </div>
            <task-progress
              :task-id="currentTask.task_id"
              @completed="handleParseCompleted"
              @retried="handleTaskRetried"
            />
          </div>
        </transition>
      </div>

      <!-- Right: Results -->
      <div class="lg:col-span-2">
        <div class="bento-card min-h-[400px]">
          <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-emerald-50 rounded-lg text-emerald-600">
                <ListIcon class="w-5 h-5" />
              </div>
              <h3 class="font-semibold">提取的事实清单</h3>
            </div>
            <span v-if="facts.length" class="text-xs font-medium px-2 py-1 bg-secondary rounded-md">
              共 {{ facts.length }} 项
            </span>
          </div>

          <div v-if="facts.length > 0">
            <facts-list :facts="facts" />
          </div>
          <div v-else class="flex flex-col items-center justify-center py-20 text-center">
            <div class="w-16 h-16 bg-secondary/50 rounded-full flex items-center justify-center mb-4">
              <FileTextIcon class="w-8 h-8 text-muted-foreground" />
            </div>
            <p class="text-muted-foreground">暂无解析出的事实数据</p>
            <p class="text-xs text-muted-foreground/60 mt-1">请在左侧上传文档并启动 AI 解析任务</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { extractFriendlyError } from '@/lib/formMessages'
import {
  ArrowLeftIcon,
  FileUpIcon,
  Loader2Icon,
  CheckCircle2Icon,
  AlertCircleIcon,
  ListIcon,
  FileTextIcon
} from 'lucide-vue-next'
import { useAIStore } from '@/stores/ai'
import FileUploader from '@/components/ai/FileUploader.vue'
import TaskProgress from '@/components/ai/TaskProgress.vue'
import FactsList from '@/components/ai/FactsList.vue'

const route = useRoute()
const router = useRouter()
const aiStore = useAIStore()

const caseId = ref(parseInt(route.params.id))
const currentTask = ref(null)
const facts = ref([])

onMounted(async () => {
  await loadFacts()
})

const loadFacts = async () => {
  try {
    await aiStore.fetchCaseFacts(caseId.value)
    facts.value = aiStore.caseFacts
  } catch (err) {
    ElMessage.error(extractFriendlyError(err, '加载事实数据失败'))
  }
}

const handleUploadSuccess = () => {
  ElMessage.success('文件上传成功，可以开始解析')
}

const handleStartParse = async (fileId) => {
  try {
    const task = await aiStore.parseDocument(caseId.value, fileId, {
      extract_parties: true,
      extract_timeline: true,
      extract_evidence: true,
      extract_laws: true,
    })
    currentTask.value = task
    ElMessage.success('解析任务已启动')
  } catch (err) {
    ElMessage.error(extractFriendlyError(err, '启动解析任务失败'))
  }
}

const handleParseCompleted = async () => {
  ElMessage.success('解析任务已完成')
  await loadFacts()
}

const handleTaskRetried = (task) => {
  currentTask.value = task
}
</script>
