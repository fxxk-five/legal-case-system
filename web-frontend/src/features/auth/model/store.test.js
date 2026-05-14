import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { mockHttp } = vi.hoisted(() => ({
  mockHttp: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('../../../shared/api/http', () => ({
  default: mockHttp,
}))

import { useAuthStore } from './store'

function createLocalStorageMock() {
  const store = new Map()
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
    clear() {
      store.clear()
    },
  }
}

describe('auth store password reset flow', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockHttp.get.mockReset()
    mockHttp.post.mockReset()

    const localStorage = createLocalStorageMock()
    vi.stubGlobal('localStorage', localStorage)
    localStorage.setItem('access_token', 'old-access')
    localStorage.setItem('refresh_token', 'old-refresh')
  })

  it('changes password and rebuilds the authenticated session', async () => {
    const authStore = useAuthStore()
    authStore.currentUser = {
      id: 1,
      phone: '13800000000',
      role: 'lawyer',
      status: 1,
      must_reset_password: true,
    }
    authStore.token = 'old-access'
    authStore.refreshToken = 'old-refresh'

    mockHttp.post.mockImplementation(async (url, payload) => {
      if (url === '/auth/password') {
        expect(payload).toEqual({ new_password: 'NewPass1234' })
        return { data: { must_reset_password: false } }
      }
      if (url === '/auth/logout') {
        expect(payload).toEqual({ refresh_token: 'old-refresh' })
        return { data: null }
      }
      if (url === '/auth/login') {
        expect(payload).toEqual({
          phone: '13800000000',
          password: 'NewPass1234',
          tenant_code: 'tenant-demo',
        })
        return {
          data: {
            access_token: 'new-access',
            refresh_token: 'new-refresh',
          },
        }
      }
      throw new Error(`unexpected POST ${url}`)
    })

    mockHttp.get.mockImplementation(async (url) => {
      if (url === '/tenants/current') {
        return {
          data: {
            tenant_code: 'tenant-demo',
            type: 'organization',
          },
        }
      }
      if (url === '/users/me') {
        return {
          data: {
            id: 1,
            phone: '13800000000',
            role: 'lawyer',
            status: 1,
            must_reset_password: false,
          },
        }
      }
      throw new Error(`unexpected GET ${url}`)
    })

    const currentUser = await authStore.changePasswordAndRebuildSession({
      newPassword: 'NewPass1234',
    })

    expect(currentUser.must_reset_password).toBe(false)
    expect(currentUser.tenant_type).toBe('organization')
    expect(authStore.currentUser.must_reset_password).toBe(false)
    expect(authStore.token).toBe('new-access')
    expect(authStore.refreshToken).toBe('new-refresh')
    expect(localStorage.getItem('access_token')).toBe('new-access')
    expect(localStorage.getItem('refresh_token')).toBe('new-refresh')
  })
})
