import { ref, watch } from 'vue'
import { useAIStore } from '@/stores/ai'
import { useWebSocket } from './useWebSocket'

const STATUS_ALIAS = {
  queued: 'pending',
  running: 'processing',
  success: 'completed',
  error: 'failed',
}

function normalizeStatus(raw) {
  if (!raw) return 'pending'
  if (STATUS_ALIAS[raw]) return STATUS_ALIAS[raw]
  if (['pending', 'processing', 'completed', 'failed'].includes(raw)) return raw
  return raw
}

function resolveTaskId(source) {
  if (typeof source === 'function') {
    return String(source() || '').trim()
  }
  if (source && typeof source === 'object' && 'value' in source) {
    return String(source.value || '').trim()
  }
  return String(source || '').trim()
}

function isTerminalStatus(taskStatus) {
  return taskStatus === 'completed' || taskStatus === 'failed'
}

export function useAITask(taskIdSource, options = {}) {
  const aiStore = useAIStore()

  const status = ref('pending')
  const progress = ref(0)
  const message = ref('')
  const completed = ref(false)
  const failed = ref(false)

  const currentTaskId = ref('')
  const lastEventTimestamp = ref('')
  const pollInterval = ref(null)

  const { connected, connecting, error: wsError, reconnect, disconnect } = useWebSocket(
    () => `/ws/ai/tasks/${currentTaskId.value || ''}`,
    {
      getQuery: () => ({ since: lastEventTimestamp.value || undefined }),
      onOpen: ({ isReconnect }) => {
        if (isReconnect) {
          pullTaskStatus({ force: true })
        }
      },
      onMessage: (payload) => {
        if (!payload || payload.task_id !== currentTaskId.value) {
          return
        }
        applyTaskEvent(payload)
      },
      onError: () => {
        pullTaskStatus({ force: true })
      },
    },
  )

  function resetTaskState() {
    status.value = 'pending'
    progress.value = 0
    message.value = ''
    completed.value = false
    failed.value = false
    lastEventTimestamp.value = ''
  }

  function syncStoreTask(taskId, patch) {
    aiStore.updateTaskProgress(taskId, patch)
  }

  function applyTerminal(taskStatus) {
    completed.value = taskStatus === 'completed'
    failed.value = taskStatus === 'failed'

    if (isTerminalStatus(taskStatus)) {
      stopPolling()
      if (taskStatus === 'completed' && typeof options.onCompleted === 'function') {
        options.onCompleted()
      }
      if (taskStatus === 'failed' && typeof options.onFailed === 'function') {
        options.onFailed(message.value)
      }
    }
  }

  function applyTaskSnapshot(task = {}, eventTimestamp = '') {
    const nextStatus = normalizeStatus(task.status)
    const nextProgress = Number(task.progress ?? 0)
    const nextMessage = task.message || task.error_message || ''

    status.value = nextStatus
    progress.value = Number.isNaN(nextProgress) ? 0 : nextProgress
    message.value = nextMessage

    if (eventTimestamp) {
      lastEventTimestamp.value = eventTimestamp
    }

    syncStoreTask(currentTaskId.value, {
      status: nextStatus,
      progress: progress.value,
      message: nextMessage,
      error_message: task.error_message || null,
    })

    applyTerminal(nextStatus)
  }

  function applyTaskEvent(payload) {
    const nextProgress = Number(payload.progress ?? 0)
    let nextStatus = 'processing'

    if (payload.type === 'completed') {
      nextStatus = 'completed'
    } else if (payload.type === 'failed') {
      nextStatus = 'failed'
    } else if (payload.type === 'progress') {
      nextStatus = nextProgress <= 0 ? 'pending' : 'processing'
    }

    applyTaskSnapshot(
      {
        status: nextStatus,
        progress: Number.isNaN(nextProgress) ? 0 : nextProgress,
        message: payload.message || payload.error || '',
        error_message: payload.error || null,
      },
      payload.timestamp || '',
    )
  }

  async function pullTaskStatus({ force = false } = {}) {
    const taskId = currentTaskId.value
    if (!taskId) return null
    if (!force && connected.value && !options.pollWhenConnected) return null
    if (completed.value || failed.value) return null

    try {
      const taskStatus = await aiStore.getTaskStatus(taskId)
      applyTaskSnapshot(taskStatus, new Date().toISOString())
      return taskStatus
    } catch (err) {
      console.error('Failed to pull AI task status:', err)
      return null
    }
  }

  function startPolling() {
    if (pollInterval.value) return

    pullTaskStatus({ force: true })
    pollInterval.value = setInterval(() => {
      pullTaskStatus()
    }, options.pollIntervalMs || 2000)
  }

  function stopPolling() {
    if (!pollInterval.value) return
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }

  watch(
    () => resolveTaskId(taskIdSource),
    (nextTaskId, prevTaskId) => {
      if (nextTaskId === prevTaskId) return

      resetTaskState()
      currentTaskId.value = nextTaskId

      if (!nextTaskId) {
        disconnect()
        stopPolling()
        return
      }

      disconnect()
      reconnect()
      pullTaskStatus({ force: true })
    },
    { immediate: true },
  )

  return {
    status,
    progress,
    message,
    completed,
    failed,
    connected,
    connecting,
    wsError,
    startPolling,
    stopPolling,
    refreshStatus: () => pullTaskStatus({ force: true }),
  }
}
