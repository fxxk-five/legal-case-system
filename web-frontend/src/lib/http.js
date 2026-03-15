import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

const http = axios.create({
  baseURL,
  timeout: 10000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('access_token')
    }
    return Promise.reject(error)
  },
)

export default http
