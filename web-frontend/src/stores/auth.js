import { defineStore } from 'pinia'

import http from '../lib/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    currentUser: null,
  }),
  actions: {
    async applyAccessToken(token) {
      this.token = token
      localStorage.setItem('access_token', this.token)
      await this.fetchCurrentUser()
    },
    async login(payload) {
      try {
        const requestPayload = {
          ...payload,
          tenant_code: payload.tenant_code?.trim() || null,
        }
        const { data } = await http.post('/auth/login', requestPayload)
        await this.applyAccessToken(data.access_token)
      } catch (error) {
        this.logout()
        throw error
      }
    },
    async fetchCurrentUser() {
      if (!this.token) {
        this.currentUser = null
        return
      }
      try {
        const { data } = await http.get('/users/me')
        this.currentUser = data
      } catch (error) {
        this.logout()
        throw error
      }
    },
    async checkBackendHealth() {
      const { data } = await http.get('/health')
      return data
    },
    logout() {
      this.token = ''
      this.currentUser = null
      localStorage.removeItem('access_token')
    },
  },
})
