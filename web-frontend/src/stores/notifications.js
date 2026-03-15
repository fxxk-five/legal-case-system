import { defineStore } from 'pinia'

import http from '../lib/http'

export const useNotificationStore = defineStore('notifications', {
  state: () => ({
    items: [],
  }),
  getters: {
    unreadCount(state) {
      return state.items.filter((item) => !item.is_read).length
    },
  },
  actions: {
    async fetchNotifications(unreadOnly = false) {
      try {
        const { data } = await http.get('/notifications', {
          params: unreadOnly ? { unread_only: true } : {},
        })
        this.items = data
      } catch {
        this.items = []
      }
    },
    async markRead(notificationId) {
      await http.patch(`/notifications/${notificationId}/read`)
      const target = this.items.find((item) => item.id === notificationId)
      if (target) {
        target.is_read = true
      }
    },
  },
})
