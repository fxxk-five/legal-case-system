import axios from 'axios'
import { ElMessage } from 'element-plus/es/components/message/index'

import {
  NETWORK_ERROR_MESSAGE,
  REQUEST_FAILED_MESSAGE,
  resolveFriendlyErrorFromPayload,
  SERVER_ERROR_MESSAGE,
  STATUS_CODE_MESSAGES,
} from '../lib/formMessages'
import { STATUS_CODE_MAP } from './statusCodeMap'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

function createRequestId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeErrorPayload(payload, status) {
  const fallbackCode = STATUS_CODE_MAP[status] || 'INTERNAL_ERROR'
  const fallbackMessage = STATUS_CODE_MESSAGES[status] || REQUEST_FAILED_MESSAGE

  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    return {
      ...payload,
      code: payload.code || fallbackCode,
      message: payload.message || payload.detail || fallbackMessage,
      detail: payload.detail || payload.message || fallbackMessage,
    }
  }

  if (Array.isArray(payload)) {
    return {
      code: fallbackCode,
      message: fallbackMessage,
      detail: payload,
    }
  }

  if (typeof payload === 'string' && payload.trim()) {
    return {
      code: fallbackCode,
      message: payload.trim(),
      detail: payload.trim(),
    }
  }

  return {
    code: fallbackCode,
    message: fallbackMessage,
    detail: fallbackMessage,
  }
}

const http = axios.create({
  baseURL,
  timeout: 10000,
})

let refreshPromise = null

function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) {
    return Promise.resolve(null)
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post(
        `${baseURL}/auth/refresh`,
        { refresh_token: refreshToken },
        {
          headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': createRequestId(),
          },
          timeout: 10000,
        },
      )
      .then((resp) => {
        const nextAccessToken = resp?.data?.access_token || ''
        const nextRefreshToken = resp?.data?.refresh_token || refreshToken
        if (!nextAccessToken) {
          return null
        }
        localStorage.setItem('access_token', nextAccessToken)
        localStorage.setItem('refresh_token', nextRefreshToken)
        return nextAccessToken
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  config.headers = config.headers || {}
  config.headers['X-Request-ID'] = config.headers['X-Request-ID'] || createRequestId()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status
    const requestConfig = error?.config || {}
    const normalizedPayload = normalizeErrorPayload(error?.response?.data, status)

    if (error?.response) {
      error.response.data = normalizedPayload
    }

    error.errorCode = normalizedPayload.code || ''
    error.requestId = normalizedPayload.request_id || requestConfig.headers?.['X-Request-ID'] || ''
    error.userMessage = resolveFriendlyErrorFromPayload(
      normalizedPayload,
      STATUS_CODE_MESSAGES[status] || REQUEST_FAILED_MESSAGE,
      status,
    )

    if (status === 401 && !requestConfig._retry && !requestConfig.skipAuthRefresh) {
      const newAccessToken = await refreshAccessToken()
      if (newAccessToken) {
        requestConfig._retry = true
        requestConfig.headers = requestConfig.headers || {}
        requestConfig.headers.Authorization = `Bearer ${newAccessToken}`
        return http(requestConfig)
      }
    }

    if (status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }

    if (requestConfig.showErrorMessage && error.userMessage) {
      ElMessage.error(error.userMessage)
    }

    // Global error toast for server errors and network failures (unless suppressed)
    if (!requestConfig.suppressGlobalError) {
      if (!error.response) {
        ElMessage.error(NETWORK_ERROR_MESSAGE)
      } else if (status >= 500) {
        ElMessage.error(SERVER_ERROR_MESSAGE)
      }
    }

    return Promise.reject(error)
  },
)

export default http
