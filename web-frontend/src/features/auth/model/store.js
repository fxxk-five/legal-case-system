import { defineStore } from 'pinia'

import http from '../../../shared/api/http'
import { normalizeRole } from '../../../shared/lib/displayText'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    currentUser: null,
  }),
  getters: {
    role: (state) => normalizeRole(state.currentUser?.role),
    mustResetPassword: (state) => Boolean(state.currentUser?.must_reset_password),
    isClient: (state) => normalizeRole(state.currentUser?.role) === 'client',
    isTenantAdmin: (state) =>
      state.currentUser?.is_tenant_admin === true || normalizeRole(state.currentUser?.role) === 'tenant_admin',
    isLawyerLike: (state) => ['lawyer', 'tenant_admin'].includes(normalizeRole(state.currentUser?.role)),
    canUseAI: (state) => ['lawyer', 'tenant_admin'].includes(normalizeRole(state.currentUser?.role)),
  },
  actions: {
    async enrichCurrentUser(user) {
      if (!user || normalizeRole(user.role) === 'client') {
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
    async ensureCurrentUser({ force = false } = {}) {
      if (!this.token) {
        this.currentUser = null
        return null
      }
      if (this.currentUser && !force) {
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
    async resolveCurrentTenantCode() {
      try {
        const { data } = await http.get('/tenants/current')
        return String(data?.tenant_code || '').trim()
      } catch {
        return ''
      }
    },
    async changePasswordAndRebuildSession({ newPassword, currentPassword = '' } = {}) {
      const user = this.currentUser || (await this.ensureCurrentUser())
      const phone = String(user?.phone || '').trim()
      if (!phone) {
        throw new Error('当前账号缺少手机号，无法在修改密码后重建登录会话。')
      }

      const payload = {
        new_password: newPassword,
      }
      if (String(currentPassword || '').trim()) {
        payload.current_password = currentPassword
      }

      await http.post('/auth/password', payload)
      const tenantCode = await this.resolveCurrentTenantCode()

      await this.logoutWithServer()
      await this.loginByPassword({
        phone,
        password: newPassword,
        tenant_code: tenantCode || null,
      })
      return this.currentUser
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
