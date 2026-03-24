import { ref, onMounted, onUnmounted } from 'vue'

function resolveWebSocketUrl(path, query = {}) {
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
  const apiUrl = new URL(apiBase, window.location.origin)
  const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'

  const baseUrl =
    path.startsWith('ws://') || path.startsWith('wss://')
      ? new URL(path)
      : new URL(`${protocol}//${apiUrl.host}${path.startsWith('/') ? path : `/${path}`}`)

  const token = localStorage.getItem('access_token')
  if (token && baseUrl.pathname.startsWith('/ws/') && !baseUrl.searchParams.has('token')) {
    baseUrl.searchParams.set('token', token)
  }

  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    baseUrl.searchParams.set(key, String(value))
  })

  return baseUrl.toString()
}

export function useWebSocket(url, options = {}) {
  const ws = ref(null)
  const connected = ref(false)
  const connecting = ref(false)
  const error = ref(null)
  const messages = ref([])
  const reconnectAttempts = ref(0)

  const reconnectDelays = options.reconnectDelays || [1000, 2000, 5000]
  const maxReconnectAttempts = reconnectDelays.length

  let reconnectTimer = null
  let manuallyClosed = false
  let everConnected = false

  const buildSocketUrl = () => {
    const query = typeof options.getQuery === 'function' ? options.getQuery() : options.query || {}
    const targetPath = typeof url === 'function' ? url() : url
    return resolveWebSocketUrl(targetPath, query)
  }

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const scheduleReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts || manuallyClosed) {
      return
    }

    const delay = reconnectDelays[reconnectAttempts.value] || reconnectDelays[reconnectDelays.length - 1] || 2000
    reconnectAttempts.value += 1
    clearReconnectTimer()

    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  const connect = () => {
    if (ws.value && [WebSocket.OPEN, WebSocket.CONNECTING].includes(ws.value.readyState)) {
      return
    }

    try {
      const wsUrl = buildSocketUrl()
      if (!wsUrl || /\/ws\/ai\/tasks\/$/.test(wsUrl)) {
        connecting.value = false
        return
      }

      connecting.value = true
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        const isReconnect = everConnected
        connected.value = true
        connecting.value = false
        error.value = null
        reconnectAttempts.value = 0
        clearReconnectTimer()
        everConnected = true

        if (typeof options.onOpen === 'function') {
          options.onOpen({ isReconnect })
        }
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          messages.value.push(data)
          if (typeof options.onMessage === 'function') {
            options.onMessage(data)
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.value.onerror = (event) => {
        error.value = 'WebSocket error occurred'
        connecting.value = false
        if (typeof options.onError === 'function') {
          options.onError(event)
        }
        console.error('WebSocket error:', event)
      }

      ws.value.onclose = (event) => {
        connected.value = false
        connecting.value = false
        ws.value = null

        if (typeof options.onClose === 'function') {
          options.onClose(event)
        }

        if (!manuallyClosed) {
          scheduleReconnect()
        }
      }
    } catch (err) {
      error.value = err.message
      connecting.value = false
      console.error('Failed to create WebSocket:', err)
      scheduleReconnect()
    }
  }

  const disconnect = () => {
    manuallyClosed = true
    clearReconnectTimer()

    if (ws.value) {
      ws.value.close()
      ws.value = null
    }

    connected.value = false
    connecting.value = false
  }

  const reconnect = () => {
    manuallyClosed = false
    clearReconnectTimer()
    connect()
  }

  const send = (data) => {
    if (ws.value && connected.value) {
      ws.value.send(JSON.stringify(data))
    }
  }

  const clearMessages = () => {
    messages.value = []
  }

  onMounted(() => {
    manuallyClosed = false
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    connecting,
    error,
    messages,
    reconnectAttempts,
    send,
    connect,
    reconnect,
    disconnect,
    clearMessages,
  }
}
