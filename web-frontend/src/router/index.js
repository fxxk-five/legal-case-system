import { createRouter, createWebHistory } from 'vue-router'

import pinia from '../stores'
import { useAuthStore } from '../stores/auth'
import AdminDashboardView from '../views/AdminDashboardView.vue'
import DashboardLayout from '../views/DashboardLayout.vue'
import CaseDetailView from '../views/CaseDetailView.vue'
import CasesView from '../views/CasesView.vue'
import LawyersView from '../views/LawyersView.vue'
import LoginView from '../views/LoginView.vue'
import OverviewView from '../views/OverviewView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/',
      component: DashboardLayout,
      children: [
        {
          path: '',
          name: 'overview',
          component: OverviewView,
        },
        {
          path: 'cases',
          name: 'cases',
          component: CasesView,
        },
        {
          path: 'cases/:id',
          name: 'case-detail',
          component: CaseDetailView,
        },
        {
          path: 'admin',
          name: 'admin',
          component: AdminDashboardView,
        },
        {
          path: 'lawyers',
          name: 'lawyers',
          component: LawyersView,
        },
        {
          path: 'settings',
          name: 'settings',
          component: SettingsView,
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore(pinia)
  if (to.meta.public) {
    return true
  }

  if (!authStore.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
