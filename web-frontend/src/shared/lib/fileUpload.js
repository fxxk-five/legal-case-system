import axios from 'axios'

import http from './http'

const FILE_EXTENSION_MIME_MAP = {
  pdf: 'application/pdf',
  doc: 'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xls: 'application/vnd.ms-excel',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  txt: 'text/plain',
}

function resolveBackendUrl(url = '') {
  if (String(url).startsWith('http')) {
    return url
  }

  const baseURL = String(http.defaults.baseURL || '').replace(/\/api\/v1\/?$/, '')
  if (String(url).startsWith('/api/v1/')) {
    return `${baseURL}${url}`
  }

  return url
}

function inferContentType(file) {
  const normalizedType = String(file?.type || '')
    .trim()
    .toLowerCase()
    .split(';', 1)[0]

  if (normalizedType.includes('/')) {
    return normalizedType
  }

  const extension = String(file?.name || '')
    .split(/[\\/]/)
    .pop()
    .split('.')
    .pop()
    .toLowerCase()

  return FILE_EXTENSION_MIME_MAP[extension] || 'application/octet-stream'
}

function normalizeUploadErrorMessage(error, fallback) {
  const payload = error?.response?.data
  if (payload && typeof payload === 'object') {
    if (typeof payload.message === 'string' && payload.message.trim()) {
      return payload.message.trim()
    }
    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return payload.detail.trim()
    }
  }

  if (typeof payload === 'string' && payload.trim()) {
    return payload.trim()
  }

  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message.trim()
  }

  return fallback
}

function emitProgress(onProgress, percent) {
  if (typeof onProgress !== 'function') {
    return
  }
  onProgress({ percent })
}

async function uploadViaServerProxy(policy, file, { description, onProgress } = {}) {
  const formData = new FormData()

  Object.entries(policy.form_fields || {}).forEach(([key, value]) => {
    formData.append(key, value)
  })
  if (description) {
    formData.append('description', description)
  }
  formData.append(policy.file_field_name || 'upload', file)

  const response = await http.request({
    url: resolveBackendUrl(policy.upload_url),
    method: policy.method || 'POST',
    data: formData,
    headers: {
      ...(policy.headers || {}),
    },
    onUploadProgress: (event) => {
      if (!event.total) {
        return
      }
      emitProgress(onProgress, Math.round((event.loaded / event.total) * 100))
    },
  })

  emitProgress(onProgress, 100)
  return response.data
}

async function uploadDirectToStorage(policy, file, { onProgress } = {}) {
  const formData = new FormData()

  Object.entries(policy.form_fields || {}).forEach(([key, value]) => {
    formData.append(key, value)
  })
  formData.append(policy.file_field_name || 'file', file)

  try {
    await axios.request({
      url: policy.upload_url,
      method: policy.method || 'POST',
      data: formData,
      headers: {
        ...(policy.headers || {}),
      },
      onUploadProgress: (event) => {
        if (!event.total) {
          return
        }
        emitProgress(onProgress, Math.round((event.loaded / event.total) * 100))
      },
    })
  } catch (error) {
    throw new Error(normalizeUploadErrorMessage(error, 'Direct upload to storage failed.'))
  }

  emitProgress(onProgress, 100)
}

export async function uploadCaseFileByPolicy(caseId, file, options = {}) {
  const response = await http.get(`/cases/${caseId}/files/upload-policy`, {
    params: {
      file_name: file?.name || 'upload-file',
      content_type: inferContentType(file),
    },
  })
  const policy = response.data

  if (policy.mode === 'direct_post') {
    if (!policy.completion_url || !policy.completion_token) {
      throw new Error('Direct upload policy is missing completion metadata.')
    }

    await uploadDirectToStorage(policy, file, options)
    const completed = await http.post(resolveBackendUrl(policy.completion_url), {
      completion_token: policy.completion_token,
      description: options.description || null,
    })
    return completed.data
  }

  return uploadViaServerProxy(policy, file, options)
}
