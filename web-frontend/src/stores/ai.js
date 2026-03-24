import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as aiApi from '@/utils/aiApi'
import { useAuthStore } from '@/stores/auth'

const AI_STATUS = {
  pending: 'pending',
  processing: 'processing',
  completed: 'completed',
  failed: 'failed',
}

const STATUS_ALIAS = {
  queued: AI_STATUS.pending,
  running: AI_STATUS.processing,
  success: AI_STATUS.completed,
  error: AI_STATUS.failed,
}

function normalizeTaskStatus(status) {
  if (!status) return AI_STATUS.pending
  if (STATUS_ALIAS[status]) return STATUS_ALIAS[status]
  if (Object.values(AI_STATUS).includes(status)) return status
  return status
}

function normalizeTask(task = {}) {
  return {
    ...task,
    task_id: task.task_id || task.id,
    status: normalizeTaskStatus(task.status),
    progress: Number(task.progress ?? 0),
  }
}

export const useAIStore = defineStore('ai', () => {
  const authStore = useAuthStore()

  const caseFacts = ref([])
  const analysisResults = ref([])
  const falsificationRecords = ref([])
  const activeTasks = ref([])
  const currentTask = ref(null)
  const taskList = ref([])
  const taskListTotal = ref(0)

  const loading = ref(false)
  const error = ref(null)

  const factsByType = computed(() => {
    const grouped = {}
    caseFacts.value.forEach((fact) => {
      if (!grouped[fact.fact_type]) {
        grouped[fact.fact_type] = []
      }
      grouped[fact.fact_type].push(fact)
    })
    return grouped
  })

  const latestAnalysis = computed(() => analysisResults.value[0] || null)

  const falsificationSummary = computed(() => {
    const total = falsificationRecords.value.length
    const falsified = falsificationRecords.value.filter((record) => record.is_falsified).length
    const critical = falsificationRecords.value.filter((record) => record.severity === 'critical').length
    const major = falsificationRecords.value.filter((record) => record.severity === 'major').length
    const minor = falsificationRecords.value.filter((record) => record.severity === 'minor').length
    return { total, falsified, critical, major, minor }
  })

  const canRetryCurrentTask = computed(() => {
    if (!authStore.canUseAI) {
      return false
    }
    return currentTask.value?.status === AI_STATUS.failed
  })

  function upsertActiveTask(task) {
    const normalized = normalizeTask(task)
    const index = activeTasks.value.findIndex((item) => item.task_id === normalized.task_id)

    if (index === -1) {
      activeTasks.value.push(normalized)
      return normalized
    }

    activeTasks.value[index] = {
      ...activeTasks.value[index],
      ...normalized,
    }
    return activeTasks.value[index]
  }

  function setCurrentTask(task) {
    const normalized = upsertActiveTask(task)
    currentTask.value = normalized
    return normalized
  }

  async function fetchCaseFacts(caseId, filters = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.getCaseFacts(caseId, filters)
      caseFacts.value = response.items
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function parseDocument(caseId, fileId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.parseDocument(caseId, fileId, options)
      return setCurrentTask(response)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAnalysisResults(caseId) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.getAnalysisResults(caseId)
      analysisResults.value = response.items
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startAnalysis(caseId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.startAnalysis(caseId, options)
      return setCurrentTask(response)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchFalsificationResults(caseId) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.getFalsificationResults(caseId)
      falsificationRecords.value = response.items
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startFalsification(caseId, analysisId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.startFalsification(caseId, analysisId, options)
      return setCurrentTask(response)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getTaskStatus(taskId) {
    try {
      const response = await aiApi.getTaskStatus(taskId)
      const normalized = normalizeTask(response)
      upsertActiveTask(normalized)

      if (currentTask.value?.task_id === taskId) {
        currentTask.value = { ...currentTask.value, ...normalized }
      }

      return normalized
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function retryTask(taskId, reason = '') {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.retryTask(taskId, reason)
      return setCurrentTask(response)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskList(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.listTasks(params)
      taskList.value = response.items || []
      taskListTotal.value = Number(response.total || 0)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function updateTaskProgress(taskId, patch = {}) {
    const normalizedPatch = {
      ...patch,
      status: patch.status ? normalizeTaskStatus(patch.status) : undefined,
    }

    const index = activeTasks.value.findIndex((task) => task.task_id === taskId)
    if (index !== -1) {
      activeTasks.value[index] = {
        ...activeTasks.value[index],
        ...normalizedPatch,
      }
    }

    if (currentTask.value?.task_id === taskId) {
      currentTask.value = {
        ...currentTask.value,
        ...normalizedPatch,
      }
    }
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    caseFacts.value = []
    analysisResults.value = []
    falsificationRecords.value = []
    activeTasks.value = []
    currentTask.value = null
    taskList.value = []
    taskListTotal.value = 0
    loading.value = false
    error.value = null
  }

  return {
    AI_STATUS,
    caseFacts,
    analysisResults,
    falsificationRecords,
    activeTasks,
    currentTask,
    taskList,
    taskListTotal,
    loading,
    error,
    factsByType,
    latestAnalysis,
    falsificationSummary,
    canRetryCurrentTask,
    fetchCaseFacts,
    parseDocument,
    fetchAnalysisResults,
    startAnalysis,
    fetchFalsificationResults,
    startFalsification,
    getTaskStatus,
    fetchTaskList,
    retryTask,
    updateTaskProgress,
    clearError,
    reset,
  }
})
