import { createRouter, createWebHistory } from 'vue-router'

import pinia from '../stores'
import {
  DASHBOARD_ROLES,
  getUnauthorizedFallbackRouteName,
  isRouteAllowedForUser,
  WEB_MAIN_ROLES,
} from '../../features/auth/lib/accessControl'
import { useAuthStore } from '../../features/auth/model/store'

const LoginView = () => import('../../pages/auth/LoginPage.vue')
const ForceResetPasswordView = () => import('../../pages/system/ForceResetPasswordPage.vue')
const PendingApprovalView = () => import('../../pages/system/PendingApprovalPage.vue')
const ClientMiniOnlyView = () => import('../../pages/system/ClientMiniOnlyPage.vue')
const AccessRestrictedView = () => import('../../pages/system/AccessRestrictedPage.vue')
const DashboardLayout = () => import('../layouts/DashboardLayout.vue')
const OverviewView = () => import('../../pages/OverviewPage.vue')
const CasesView = () => import('../../pages/cases/CasesPage.vue')
const CaseDetailView = () => import('../../pages/cases/CaseDetailPage.vue')
const DocumentParsingView = () => import('../../pages/ai/DocumentParsingPage.vue')
const ClientsView = () => import('../../pages/ClientsPage.vue')
const LawyersView = () => import('../../pages/LawyersPage.vue')
const AdminDashboardView = () => import('../../pages/AdminDashboardPage.vue')
const SuperAdminTenantsView = () => import('../../pages/SuperAdminTenantsPage.vue')
const SuperAdminUsersView = () => import('../../pages/SuperAdminUsersPage.vue')

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
      path: '/force-reset-password',
      name: 'force-reset-password',
      component: ForceResetPasswordView,
      meta: { requiresAuth: true, title: '首次改密' },
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

  // 验证用户信息，确保token有效且角色信息最新
  try {
    await authStore.ensureCurrentUser()
  } catch {
    // Token无效或后端返回错误，重定向到登录页
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  const user = authStore.currentUser
  if (!user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 强制密码重置检查：必须先完成改密才能访问其他页面
  if (user.must_reset_password && to.name !== 'force-reset-password') {
    return {
      name: 'force-reset-password',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  // 已完成改密的用户不应访问改密页面
  if (!user.must_reset_password && to.name === 'force-reset-password') {
    const rawRedirect = String(to.query?.redirect || '').trim()
    const BLOCKED = ['/force-reset-password', '/pending-approval', '/client-mini-only', '/access-restricted', '/login']
    const safeFallback = rawRedirect && !BLOCKED.some((p) => rawRedirect === p || rawRedirect.startsWith(p + '?'))
    return safeFallback ? rawRedirect : { name: getUnauthorizedFallbackRouteName(user) }
  }

  // 角色权限检查：验证用户角色是否允许访问目标路由
  if (!isRouteAllowedForUser(user, to)) {
    return { name: getUnauthorizedFallbackRouteName(user) }
  }

  return true
})

export default router
