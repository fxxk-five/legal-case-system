export const AI_TASK_STATUS_ALIAS = Object.freeze({
  queued: 'pending',
  running: 'processing',
  success: 'completed',
  error: 'failed',
})

export const AI_TASK_PENDING_STATUSES = Object.freeze(['pending', 'queued'])
export const AI_TASK_ACTIVE_STATUSES = Object.freeze(['processing', 'running', 'retrying'])
export const AI_TASK_SUCCESS_STATUSES = Object.freeze(['completed', 'success'])
export const AI_TASK_FAILURE_STATUSES = Object.freeze(['failed', 'error', 'dead'])
export const AI_TASK_TERMINAL_STATUSES = Object.freeze(['completed', 'failed', 'dead'])

const PENDING_SET = new Set(AI_TASK_PENDING_STATUSES)
const ACTIVE_SET = new Set(AI_TASK_ACTIVE_STATUSES)
const SUCCESS_SET = new Set(AI_TASK_SUCCESS_STATUSES)
const FAILURE_SET = new Set(AI_TASK_FAILURE_STATUSES)
const TERMINAL_SET = new Set(AI_TASK_TERMINAL_STATUSES)

export function normalizeAITaskStatus(rawStatus) {
  const normalized = String(rawStatus || '').trim().toLowerCase()
  if (!normalized) {
    return 'pending'
  }
  return AI_TASK_STATUS_ALIAS[normalized] || normalized
}

export function isAITaskPending(status) {
  return PENDING_SET.has(normalizeAITaskStatus(status))
}

export function isAITaskActive(status) {
  return ACTIVE_SET.has(normalizeAITaskStatus(status))
}

export function isAITaskInFlight(status) {
  return isAITaskPending(status) || isAITaskActive(status)
}

export function isAITaskSucceeded(status) {
  return SUCCESS_SET.has(normalizeAITaskStatus(status))
}

export function isAITaskFailed(status) {
  return FAILURE_SET.has(normalizeAITaskStatus(status))
}

export function isAITaskTerminal(status) {
  return TERMINAL_SET.has(normalizeAITaskStatus(status))
}

export function getAITaskStatusText(status) {
  const normalized = normalizeAITaskStatus(status)
  const textMap = {
    pending: '排队中',
    processing: '执行中',
    retrying: '重试中',
    completed: '成功',
    failed: '失败',
    dead: '终止（死信）',
  }
  return textMap[normalized] || '处理中'
}

export function resolveAITaskStatusFromEvent({
  eventType,
  eventStatus,
  progress,
} = {}) {
  const fromPayload = normalizeAITaskStatus(eventStatus)
  if (fromPayload && fromPayload !== 'pending') {
    return fromPayload
  }

  if (eventType === 'completed') {
    return 'completed'
  }
  if (eventType === 'failed') {
    return 'failed'
  }

  const normalizedProgress = Number(progress ?? 0)
  if (!Number.isFinite(normalizedProgress) || normalizedProgress <= 0) {
    return 'pending'
  }
  return 'processing'
}
