import http from '@/lib/http'

const API_BASE = '/ai'

function createIdempotencyKey(prefix = 'ai-task') {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeFact(item) {
  const metadata = item?.metadata || {}
  return {
    ...item,
    description: item?.description || item?.content || '',
    occurrence_time: item?.occurrence_time || metadata.date || null,
    evidence_id: item?.evidence_id ?? metadata.evidence_id ?? null,
  }
}

function normalizeAnalysis(item) {
  const resultData = item?.result_data || {}
  return {
    ...item,
    summary: item?.summary || resultData.summary || resultData.legal_opinion || '',
    win_rate: Number(item?.win_rate ?? resultData.win_rate ?? 0),
  }
}

function normalizeFalsification(item) {
  return {
    ...item,
    fact_description: item?.fact_description || item?.challenge_question || '',
    reason: item?.reason || item?.response || '',
    evidence_gap: item?.evidence_gap || item?.improvement_suggestion || null,
  }
}

function normalizeTask(task) {
  return {
    ...task,
    task_id: task?.task_id || task?.id,
  }
}

function withIdempotencyHeaders(headers = {}, key) {
  return {
    ...headers,
    'Idempotency-Key': key || createIdempotencyKey(),
  }
}

export function getCaseFacts(caseId, params = {}) {
  return http
    .get(`${API_BASE}/cases/${caseId}/facts`, { params })
    .then(({ data }) => ({
      ...data,
      items: (data.items || []).map(normalizeFact),
    }))
}

export function parseDocument(caseId, fileId, options = {}, idempotencyKey) {
  return http
    .post(
      `${API_BASE}/cases/${caseId}/parse-document`,
      {
        file_id: fileId,
        parse_options: options,
      },
      {
        headers: withIdempotencyHeaders({}, idempotencyKey),
      },
    )
    .then(({ data }) => normalizeTask(data))
}

export function getAnalysisResults(caseId) {
  return http
    .get(`${API_BASE}/cases/${caseId}/analysis-results`)
    .then(({ data }) => ({
      ...data,
      items: (data.items || []).map(normalizeAnalysis),
    }))
}

export function startAnalysis(caseId, options = {}, idempotencyKey) {
  return http
    .post(`${API_BASE}/cases/${caseId}/analyze`, options, {
      headers: withIdempotencyHeaders({}, idempotencyKey),
    })
    .then(({ data }) => normalizeTask(data))
}

export function getFalsificationResults(caseId) {
  return http
    .get(`${API_BASE}/cases/${caseId}/falsification-results`)
    .then(({ data }) => ({
      ...data,
      items: (data.items || []).map(normalizeFalsification),
    }))
}

export function startFalsification(caseId, analysisId, options = {}, idempotencyKey) {
  return http
    .post(
      `${API_BASE}/cases/${caseId}/falsification`,
      {
        analysis_id: analysisId,
        ...options,
      },
      {
        headers: withIdempotencyHeaders({}, idempotencyKey),
      },
    )
    .then(({ data }) => normalizeTask(data))
}

export function getTaskStatus(taskId) {
  return http
    .get(`${API_BASE}/tasks/${taskId}`)
    .then(({ data }) => normalizeTask(data))
}

export function listTasks(params = {}) {
  return http
    .get(`${API_BASE}/tasks`, { params })
    .then(({ data }) => ({
      ...data,
      items: (data.items || []).map(normalizeTask),
    }))
}

export function retryTask(taskId, reason = '') {
  return http
    .post(`${API_BASE}/tasks/${taskId}/retry`, { reason: reason || null })
    .then(({ data }) => normalizeTask(data))
}
