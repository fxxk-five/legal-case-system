import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as aiApi from '@/features/ai-tasks/api/domain-api'
import { useAuthStore } from '@/features/auth/model/store'
import { normalizeAITaskStatus } from '@/features/ai-tasks/model/trackingPolicy'
import { extractFriendlyError } from '@/shared/lib/formMessages'

const AI_STATUS = {
  pending: 'pending',
  processing: 'processing',
  retrying: 'retrying',
  completed: 'completed',
  failed: 'failed',
  dead: 'dead',
}

function normalizeTaskStatus(status) {
  return normalizeAITaskStatus(status)
}

function normalizeTask(task = {}) {
  return {
    ...task,
    task_id: task.task_id || task.id,
    status: normalizeTaskStatus(task.status),
    progress: Number(task.progress ?? 0),
  }
}

function normalizeCaseId(caseId) {
  const parsed = Number(caseId || 0)
  return Number.isFinite(parsed) && parsed > 0 ? Math.round(parsed) : 0
}

function normalizeTaskType(taskType) {
  return String(taskType || '').trim().toLowerCase()
}

function toTimestamp(value) {
  if (!value) return 0
  const timestamp = Date.parse(String(value))
  return Number.isFinite(timestamp) ? timestamp : 0
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

  function setStoreError(err, fallback = '操作失败') {
    error.value = extractFriendlyError(err, fallback)
  }

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

  function clearCurrentTask() {
    currentTask.value = null
  }

  async function fetchCaseFacts(caseId, filters = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await aiApi.getCaseFacts(caseId, filters)
      caseFacts.value = response.items
      return response
    } catch (err) {
      setStoreError(err, '案件事实加载失败。')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function parseDocument(caseId, fileId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const idempotencyKey = `parse-${authStore.user?.tenant_id || 0}-${caseId}-${Date.now()}`
      const response = await aiApi.parseDocument(caseId, fileId, options, idempotencyKey)
      return setCurrentTask(response)
    } catch (err) {
      setStoreError(err, '文档解析任务创建失败。')
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
      setStoreError(err, '分析结果加载失败。')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startAnalysis(caseId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const idempotencyKey = `analysis-${authStore.user?.tenant_id || 0}-${caseId}-${Date.now()}`
      const response = await aiApi.startAnalysis(caseId, options, idempotencyKey)
      return setCurrentTask(response)
    } catch (err) {
      setStoreError(err, '法律分析任务创建失败。')
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
      setStoreError(err, '证伪结果加载失败。')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startFalsification(caseId, analysisId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const idempotencyKey = `falsification-${authStore.user?.tenant_id || 0}-${caseId}-${Date.now()}`
      const response = await aiApi.startFalsification(caseId, analysisId, options, idempotencyKey)
      return setCurrentTask(response)
    } catch (err) {
      setStoreError(err, '证伪任务创建失败。')
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
      setStoreError(err, '任务状态获取失败。')
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
      setStoreError(err, '任务重试失败。')
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
      setStoreError(err, '任务列表加载失败。')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function restoreCaseTaskFeedback({
    caseId,
    taskType,
    preferredTaskId = '',
    pageSize = 20,
  } = {}) {
    const normalizedCaseId = normalizeCaseId(caseId)
    const normalizedTaskType = normalizeTaskType(taskType)
    if (!normalizedCaseId || !normalizedTaskType) {
      return null
    }

    const preferredId = String(preferredTaskId || '').trim()
    if (preferredId) {
      try {
        const preferredTask = await getTaskStatus(preferredId)
        if (
          normalizeCaseId(preferredTask?.case_id) === normalizedCaseId
          && normalizeTaskType(preferredTask?.task_type) === normalizedTaskType
        ) {
          return setCurrentTask(preferredTask)
        }
      } catch {
        // Best-effort restore; fall back to list query.
      }
    }

    try {
      const response = await fetchTaskList({
        page: 1,
        page_size: pageSize,
        task_type: normalizedTaskType,
      })

      const matched = (response.items || [])
        .filter(
          (item) =>
            normalizeCaseId(item?.case_id) === normalizedCaseId
            && normalizeTaskType(item?.task_type) === normalizedTaskType,
        )
        .sort((left, right) => toTimestamp(right?.created_at) - toTimestamp(left?.created_at))

      if (!matched.length) {
        return null
      }

      return setCurrentTask(matched[0])
    } catch {
      return null
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
    setCurrentTask,
    clearCurrentTask,
    fetchTaskList,
    restoreCaseTaskFeedback,
    retryTask,
    updateTaskProgress,
    clearError,
    reset,
  }
})
