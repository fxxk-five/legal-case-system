import { defineStore } from 'pinia'

import http from '../lib/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    currentUser: null,
  }),
  actions: {
    async login(payload) {
      const { data } = await http.post('/auth/login', payload)
      this.token = data.access_token
      localStorage.setItem('access_token', this.token)
      await this.fetchCurrentUser()
    },
    async fetchCurrentUser() {
      if (!this.token) {
        this.currentUser = null
        return
      }
      const { data } = await http.get('/users/me')
      this.currentUser = data
    },
    logout() {
      this.token = ''
      this.currentUser = null
      localStorage.removeItem('access_token')
    },
  },
})
