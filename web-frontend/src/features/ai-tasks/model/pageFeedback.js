const AI_TASK_FEEDBACK_VERSION = '2026-03-25-v1'
const AI_TASK_FEEDBACK_PREFIX = `legal_case_ai_feedback_${AI_TASK_FEEDBACK_VERSION}`

function normalizeCaseId(caseId) {
  const parsed = Number(caseId || 0)
  return Number.isFinite(parsed) && parsed > 0 ? String(Math.round(parsed)) : ''
}

function normalizeTaskType(taskType) {
  return String(taskType || '').trim().toLowerCase()
}

function resolveStorage(storage) {
  if (storage) {
    return storage
  }
  if (typeof window === 'undefined' || !window.localStorage) {
    return null
  }
  return window.localStorage
}

function buildHintKey({ caseId, taskType }) {
  const normalizedCaseId = normalizeCaseId(caseId)
  const normalizedTaskType = normalizeTaskType(taskType)
  if (!normalizedCaseId || !normalizedTaskType) {
    return ''
  }
  return `${AI_TASK_FEEDBACK_PREFIX}:${normalizedCaseId}:${normalizedTaskType}`
}

export function loadAITaskFeedbackHint({ caseId, taskType, storage } = {}) {
  const key = buildHintKey({ caseId, taskType })
  const targetStorage = resolveStorage(storage)
  if (!key || !targetStorage?.getItem) {
    return ''
  }

  try {
    return String(targetStorage.getItem(key) || '').trim()
  } catch {
    return ''
  }
}

export function saveAITaskFeedbackHint({ caseId, taskType, taskId, storage } = {}) {
  const key = buildHintKey({ caseId, taskType })
  const targetStorage = resolveStorage(storage)
  const normalizedTaskId = String(taskId || '').trim()
  if (!key || !targetStorage?.setItem || !normalizedTaskId) {
    return false
  }

  try {
    targetStorage.setItem(key, normalizedTaskId)
    return true
  } catch {
    return false
  }
}

export function clearAITaskFeedbackHint({ caseId, taskType, storage } = {}) {
  const key = buildHintKey({ caseId, taskType })
  const targetStorage = resolveStorage(storage)
  if (!key || !targetStorage?.removeItem) {
    return false
  }

  try {
    targetStorage.removeItem(key)
    return true
  } catch {
    return false
  }
}
