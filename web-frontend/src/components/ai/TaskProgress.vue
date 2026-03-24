<template>
  <div class="py-4 px-5 rounded-2xl border border-border bg-white shadow-sm space-y-4">
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-3">
        <div :class="[
          'w-2 h-2 rounded-full',
          status === 'processing' || status === 'running' ? 'bg-blue-400 animate-pulse' : statusColorClass
        ]"></div>
        <span class="text-sm font-semibold text-gray-700">{{ displayMessage }}</span>
      </div>
      <span class="text-sm font-bold text-[#007AFF] tabular-nums">{{ normalizedProgress }}%</span>
    </div>

    <div class="relative h-2 w-full bg-gray-100 rounded-full overflow-hidden">
      <div
        class="absolute top-0 left-0 h-full transition-all duration-500 ease-out rounded-full"
        :class="progressColorClass"
        :style="{ width: `${normalizedProgress}%` }"
      ></div>
    </div>

    <div v-if="canRetry" class="flex justify-end pt-1">
      <button
        type="button"
        :disabled="retrying"
        class="apple-btn-secondary !py-1 !px-3 !text-xs !text-red-500 !border-red-200 hover:!bg-red-50"
        @click="handleRetry"
      >
        <RefreshCwIcon v-if="!retrying" class="w-3 h-3" />
        {{ retrying ? '重试提交中...' : '失败重试' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { RefreshCwIcon } from 'lucide-vue-next'
import { useAITask } from '@/composables/useAITask'
import { useAIStore } from '@/stores/ai'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  taskId: {
    type: String,
    required: true,
  },
  allowRetry: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['completed', 'failed', 'retried'])

const aiStore = useAIStore()
const authStore = useAuthStore()
const retrying = ref(false)

const { status, progress, message, connecting, startPolling, stopPolling } = useAITask(() => props.taskId, {
  onCompleted: () => emit('completed'),
  onFailed: (errorMessage) => emit('failed', errorMessage),
})

const normalizedProgress = computed(() => {
  const value = Number(progress.value ?? 0)
  if (Number.isNaN(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
})

const canRetry = computed(() => {
  if (!props.allowRetry) return false
  if (!authStore.canUseAI) return false
  return status.value === 'failed'
})

const displayMessage = computed(() => {
  if (message.value) return message.value
  if (connecting.value && !message.value) return '进度通道连接中...'
  return getStatusText(status.value)
})

const statusColorClass = computed(() => {
  switch (status.value) {
    case 'completed':
    case 'success':
      return 'bg-green-500'
    case 'failed':
    case 'error':
      return 'bg-red-500'
    case 'pending':
    case 'queued':
      return 'bg-orange-400'
    default:
      return 'bg-[#007AFF]'
  }
})

const progressColorClass = computed(() => {
  switch (status.value) {
    case 'completed':
    case 'success':
      return 'bg-green-500'
    case 'failed':
    case 'error':
      return 'bg-red-500'
    default:
      return 'bg-[#007AFF]'
  }
})

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

async function handleRetry() {
  if (!props.taskId || retrying.value) {
    return
  }

  retrying.value = true
  try {
    const nextTask = await aiStore.retryTask(props.taskId, 'manual_retry_from_web')
    ElMessage.success('已提交重试任务')
    emit('retried', nextTask)
  } catch {
    ElMessage.error(aiStore.error || '提交重试失败')
  } finally {
    retrying.value = false
  }
}

function getStatusText(taskStatus) {
  const texts = {
    pending: '排队中',
    queued: '排队中',
    processing: '执行中',
    running: '执行中',
    completed: '成功',
    success: '成功',
    failed: '失败',
    error: '失败',
  }
  return texts[taskStatus] || '处理中'
}

</script>

<style>
.apple-progress .el-progress-bar__outer {
  @apply !bg-gray-100 !rounded-full;
}
.apple-progress .el-progress-bar__inner {
  @apply !rounded-full transition-all duration-500 ease-out;
}
</style>
