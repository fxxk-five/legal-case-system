import { defineStore } from 'pinia'

import http from '../lib/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    currentUser: null,
  }),
  getters: {
    role: (state) => state.currentUser?.role || '',
    isClient: (state) => state.currentUser?.role === 'client',
    isTenantAdmin: (state) =>
      state.currentUser?.is_tenant_admin === true || state.currentUser?.role === 'tenant_admin',
    isLawyerLike: (state) => ['lawyer', 'tenant_admin'].includes(state.currentUser?.role),
    canUseAI: (state) => ['lawyer', 'tenant_admin'].includes(state.currentUser?.role),
  },
  actions: {
    async enrichCurrentUser(user) {
      if (!user || user.role === 'client') {
        return user
      }

      try {
        const { data: tenant } = await http.get('/tenants/current')
        if (!tenant?.type) {
          return user
        }
        return {
          ...user,
          tenant_type: tenant.type,
        }
      } catch {
        return user
      }
    },
    async applyTokens(accessToken, refreshToken = '') {
      this.token = accessToken || ''
      this.refreshToken = refreshToken || ''
      localStorage.setItem('access_token', this.token)
      if (this.refreshToken) {
        localStorage.setItem('refresh_token', this.refreshToken)
      } else {
        localStorage.removeItem('refresh_token')
      }
      await this.fetchCurrentUser()
    },
    async login(payload) {
      try {
        const requestPayload = {
          ...payload,
          tenant_code: payload.tenant_code?.trim() || null,
        }
        const { data } = await http.post('/auth/login', requestPayload)
        await this.applyTokens(data.access_token, data.refresh_token || '')
      } catch (error) {
        this.logout()
        throw error
      }
    },
    async loginByPassword(payload) {
      return this.login(payload)
    },
    async loginBySmsCode(payload) {
      try {
        const requestPayload = {
          ...payload,
          phone: payload.phone?.trim() || '',
          code: payload.code?.trim() || '',
          tenant_code: payload.tenant_code?.trim() || null,
        }
        const { data } = await http.post('/auth/sms-login', requestPayload)
        await this.applyTokens(data.access_token, data.refresh_token || '')
      } catch (error) {
        this.logout()
        throw error
      }
    },
    async ensureCurrentUser() {
      if (!this.token) {
        this.currentUser = null
        return null
      }
      if (this.currentUser) {
        return this.currentUser
      }
      await this.fetchCurrentUser()
      return this.currentUser
    },
    async fetchCurrentUser() {
      if (!this.token) {
        this.currentUser = null
        return null
      }
      try {
        const { data } = await http.get('/users/me')
        const enrichedUser = await this.enrichCurrentUser(data)
        this.currentUser = enrichedUser
        return enrichedUser
      } catch (error) {
        this.logout()
        throw error
      }
    },
    async checkBackendHealth() {
      const { data } = await http.get('/health')
      return data
    },
    async logoutWithServer() {
      const refreshToken = this.refreshToken || localStorage.getItem('refresh_token') || ''
      try {
        await http.post(
          '/auth/logout',
          { refresh_token: refreshToken || null },
          { skipAuthRefresh: true },
        )
      } catch {
        // Ignore server-side logout failures; local cleanup still applies.
      } finally {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.refreshToken = ''
      this.currentUser = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },
  },
})
