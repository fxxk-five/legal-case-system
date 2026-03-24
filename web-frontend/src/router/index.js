import { createRouter, createWebHistory } from 'vue-router'

import pinia from '../stores'
import {
  DASHBOARD_ROLES,
  getUnauthorizedFallbackRouteName,
  isRouteAllowedForUser,
  WEB_MAIN_ROLES,
} from '../lib/accessControl'
import { useAuthStore } from '../stores/auth'

const LoginView = () => import('../views/LoginView.vue')
const PendingApprovalView = () => import('../views/PendingApprovalView.vue')
const ClientMiniOnlyView = () => import('../views/ClientMiniOnlyView.vue')
const AccessRestrictedView = () => import('../views/AccessRestrictedView.vue')
const DashboardLayout = () => import('../views/DashboardLayout.vue')
const OverviewView = () => import('../views/OverviewView.vue')
const CasesView = () => import('../views/CasesView.vue')
const CaseDetailView = () => import('../views/CaseDetailView.vue')
const DocumentParsingView = () => import('../views/ai/DocumentParsing.vue')
const ClientsView = () => import('../views/ClientsView.vue')
const LawyersView = () => import('../views/LawyersView.vue')
const AdminDashboardView = () => import('../views/AdminDashboardView.vue')
const SuperAdminTenantsView = () => import('../views/SuperAdminTenantsView.vue')
const SuperAdminUsersView = () => import('../views/SuperAdminUsersView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true, title: '登录' },
    },
    {
      path: '/pending-approval',
      name: 'pending-approval',
      component: PendingApprovalView,
      meta: { requiresAuth: true, title: '等待审批' },
    },
    {
      path: '/client-mini-only',
      name: 'client-mini-only',
      component: ClientMiniOnlyView,
      meta: { requiresAuth: true, allowRoles: ['client'], title: '当事人请使用小程序' },
    },
    {
      path: '/access-restricted',
      name: 'access-restricted',
      component: AccessRestrictedView,
      meta: { requiresAuth: true, title: '访问受限' },
    },
    {
      path: '/',
      component: DashboardLayout,
      meta: { requiresAuth: true, allowRoles: DASHBOARD_ROLES },
      children: [
        {
          path: '',
          name: 'overview',
          component: OverviewView,
          meta: { allowRoles: WEB_MAIN_ROLES, title: '概览' },
        },
        {
          path: 'cases',
          name: 'cases',
          component: CasesView,
          meta: { allowRoles: WEB_MAIN_ROLES, title: '案件管理' },
        },
        {
          path: 'cases/:id',
          name: 'case-detail',
          component: CaseDetailView,
          meta: { allowRoles: WEB_MAIN_ROLES, title: '案件详情' },
        },
        {
          path: 'cases/:id/ai/parse',
          name: 'DocumentParsing',
          component: DocumentParsingView,
          meta: { allowRoles: WEB_MAIN_ROLES, title: '文档解析' },
        },
        {
          path: 'cases/:id/ai/analyze',
          name: 'LegalAnalysis',
          redirect: (to) => ({ name: 'DocumentParsing', params: { id: to.params.id } }),
        },
        {
          path: 'cases/:id/ai/falsify',
          name: 'Falsification',
          redirect: (to) => ({ name: 'DocumentParsing', params: { id: to.params.id } }),
        },
        {
          path: 'clients',
          name: 'clients',
          component: ClientsView,
          meta: { allowRoles: WEB_MAIN_ROLES, title: '当事人管理' },
        },
        {
          path: 'clients/:id',
          name: 'client-detail',
          component: ClientsView,
          meta: { allowRoles: WEB_MAIN_ROLES, title: '当事人详情' },
        },
        {
          path: 'analysis',
          name: 'analysis',
          redirect: { name: 'overview' },
        },
        {
          path: 'lawyers',
          name: 'lawyers',
          component: LawyersView,
          meta: { allowRoles: ['tenant_admin'], title: '律师管理' },
        },
        {
          path: 'super-admin',
          name: 'super-admin-overview',
          component: AdminDashboardView,
          meta: { allowRoles: ['super_admin'], title: '平台概览' },
        },
        {
          path: 'super-admin/tenants',
          name: 'super-admin-tenants',
          component: SuperAdminTenantsView,
          meta: { allowRoles: ['super_admin'], title: '租户管理' },
        },
        {
          path: 'super-admin/users',
          name: 'super-admin-users',
          component: SuperAdminUsersView,
          meta: { allowRoles: ['super_admin'], title: '用户总览' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  if (to.meta?.public) {
    return true
  }

  if (!authStore.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  try {
    await authStore.ensureCurrentUser()
  } catch {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  const user = authStore.currentUser
  if (!user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (!isRouteAllowedForUser(user, to)) {
    return { name: getUnauthorizedFallbackRouteName(user) }
  }

  return true
})

export default router
