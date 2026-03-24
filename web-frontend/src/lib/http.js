import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

const STATUS_CODE_MAP = {
  400: 'VALIDATION_ERROR',
  401: 'AUTH_REQUIRED',
  403: 'FORBIDDEN',
  404: 'RESOURCE_NOT_FOUND',
  409: 'CONFLICT',
  413: 'PAYLOAD_TOO_LARGE',
  415: 'UNSUPPORTED_MEDIA_TYPE',
  422: 'VALIDATION_ERROR',
  500: 'INTERNAL_ERROR',
  502: 'EXTERNAL_SERVICE_ERROR',
  503: 'EXTERNAL_SERVICE_ERROR',
  504: 'EXTERNAL_SERVICE_ERROR',
}

const STATUS_MESSAGE_MAP = {
  413: '上传文件过大，请压缩后重试。',
  415: '文件格式不受支持，请更换文件后重试。',
}

function createRequestId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
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
    const payload = error?.response?.data
    const requestConfig = error?.config || {}

    if (payload && typeof payload === 'object') {
      const fallbackCode = STATUS_CODE_MAP[status] || 'INTERNAL_ERROR'
      const fallbackMessage = STATUS_MESSAGE_MAP[status] || '请求失败。'
      payload.code = payload.code || fallbackCode
      payload.message = payload.message || payload.detail || fallbackMessage
      payload.detail = payload.detail || payload.message || fallbackMessage
    }

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

    return Promise.reject(error)
  },
)

export default http
