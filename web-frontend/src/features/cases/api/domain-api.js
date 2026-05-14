import http from '../../../shared/api/http'
import { uploadCaseFileByPolicy } from '../../../shared/lib/fileUpload'

function normalizeNumericId(value, fieldName) {
  const parsed = Number(value || 0)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${fieldName} is invalid`)
  }
  return parsed
}

function normalizeRemarkText(value) {
  return String(value === null || value === undefined ? '' : value).trim()
}

function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '')
  if (!entries.length) {
    return ''
  }
  const query = entries
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return `?${query}`
}

export const casesApi = {
  async listCases({ httpClient = http } = {}) {
    const { data } = await httpClient.get('/cases')
    return Array.isArray(data) ? data : []
  },
  async getCaseDetail(caseId, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/cases/${normalizeNumericId(caseId, 'caseId')}`)
    return data || null
  },
  async updateCaseStatus(caseId, status, { httpClient = http } = {}) {
    const { data } = await httpClient.patch(`/cases/${normalizeNumericId(caseId, 'caseId')}`, { status })
    return data || null
  },
  async getCaseInviteQrcode(caseId, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/cases/${normalizeNumericId(caseId, 'caseId')}/invite-qrcode`)
    return data || null
  },
  async getLatestReportAccessLink(caseId, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/cases/${normalizeNumericId(caseId, 'caseId')}/report/access-link`)
    return data || null
  },
  async getReportVersionAccessLink(caseId, reportName, { httpClient = http } = {}) {
    const safeReportName = encodeURIComponent(String(reportName || '').trim())
    const { data } = await httpClient.get(
      `/cases/${normalizeNumericId(caseId, 'caseId')}/reports/${safeReportName}/access-link`,
    )
    return data || null
  },
}

export const filesApi = {
  async listCaseFiles(caseId, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/files/case/${normalizeNumericId(caseId, 'caseId')}`)
    return Array.isArray(data) ? data : []
  },
  async uploadCaseFile(
    caseId,
    file,
    options = {},
    { uploader = uploadCaseFileByPolicy } = {},
  ) {
    return uploader(normalizeNumericId(caseId, 'caseId'), file, options)
  },
  async getFileAccessLink(fileId, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/files/${normalizeNumericId(fileId, 'fileId')}/access-link`)
    return data || null
  },
  async deleteFile(fileId, { httpClient = http } = {}) {
    const { data } = await httpClient.delete(`/files/${normalizeNumericId(fileId, 'fileId')}`)
    return data || null
  },
}

export const remarksApi = {
  async updateClientRemark(caseId, remark, { httpClient = http } = {}) {
    const { data } = await httpClient.patch(`/cases/${normalizeNumericId(caseId, 'caseId')}/client-remark`, {
      client_remark: normalizeRemarkText(remark),
    })
    return data || null
  },
  async updateLawyerRemark(caseId, remark, { httpClient = http } = {}) {
    const { data } = await httpClient.patch(`/cases/${normalizeNumericId(caseId, 'caseId')}/lawyer-remark`, {
      lawyer_remark: normalizeRemarkText(remark),
    })
    return data || null
  },
}

export const aiTasksApi = {
  async listTasks(params = {}, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/ai/tasks${buildQuery(params)}`)
    return data || null
  },
  async getTaskStatus(taskId, { httpClient = http } = {}) {
    const safeTaskId = encodeURIComponent(String(taskId || '').trim())
    const { data } = await httpClient.get(`/ai/tasks/${safeTaskId}`)
    return data || null
  },
  async retryTask(taskId, reason = '', { httpClient = http } = {}) {
    const safeTaskId = encodeURIComponent(String(taskId || '').trim())
    const { data } = await httpClient.post(`/ai/tasks/${safeTaskId}/retry`, {
      reason: reason || null,
    })
    return data || null
  },
  async getCaseAnalysisResults(caseId, { httpClient = http } = {}) {
    const { data } = await httpClient.get(`/ai/cases/${normalizeNumericId(caseId, 'caseId')}/analysis-results`)
    return data || { items: [] }
  },
}

