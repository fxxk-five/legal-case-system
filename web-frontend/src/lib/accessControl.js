export const WEB_NAV_ROLES = ['tenant_admin', 'lawyer']
export const WEB_MAIN_ROLES = WEB_NAV_ROLES
export const DASHBOARD_ROLES = [...WEB_MAIN_ROLES, 'super_admin']

const ROLE_LANDING_ROUTE_MAP = {
  tenant_admin: 'overview',
  lawyer: 'overview',
  client: 'client-mini-only',
  super_admin: 'super-admin-overview',
}

const BLOCKED_PAGE_NAMES = ['pending-approval', 'client-mini-only', 'access-restricted']
const RESTRICTED_LANDING_ROUTE_NAMES = new Set(BLOCKED_PAGE_NAMES)
const PERSONAL_WORKSPACE_ALLOWED_ROUTE_NAMES = new Set([
  'cases',
  'case-detail',
  'DocumentParsing',
  'LegalAnalysis',
  'Falsification',
])

export const DASHBOARD_NAV_ITEMS = [
  {
    key: 'super-admin-overview',
    label: '平台概览',
    to: '/super-admin',
    icon: 'ShieldIcon',
    allowRoles: ['super_admin'],
  },
  {
    key: 'super-admin-tenants',
    label: '租户管理',
    to: '/super-admin/tenants',
    icon: 'Building2Icon',
    allowRoles: ['super_admin'],
  },
  {
    key: 'super-admin-users',
    label: '用户总览',
    to: '/super-admin/users',
    icon: 'UsersIcon',
    allowRoles: ['super_admin'],
  },
  {
    key: 'overview',
    label: '概览',
    to: '/',
    icon: 'LayoutDashboardIcon',
    allowRoles: ['tenant_admin', 'lawyer'],
  },
  {
    key: 'cases',
    label: '案件管理',
    to: '/cases',
    icon: 'BriefcaseIcon',
    allowRoles: ['tenant_admin', 'lawyer'],
  },
  {
    key: 'clients',
    label: '当事人管理',
    to: '/clients',
    icon: 'UserIcon',
    allowRoles: ['tenant_admin', 'lawyer'],
  },
  {
    key: 'lawyers',
    label: '律师管理',
    to: '/lawyers',
    icon: 'UsersIcon',
    allowRoles: ['tenant_admin'],
  },
]

export function isUserApproved(user) {
  return Number(user?.status) === 1
}

export function isMainWebRole(role) {
  return WEB_NAV_ROLES.includes(role)
}

export function isDashboardRole(role) {
  return DASHBOARD_ROLES.includes(role)
}

export function isPersonalWorkspaceUser(user) {
  return Boolean(user && user.tenant_type === 'personal' && isMainWebRole(user.role))
}

function isRestrictedLandingRouteName(routeName) {
  return RESTRICTED_LANDING_ROUTE_NAMES.has(routeName)
}

function getRoleLandingRouteName(role) {
  return ROLE_LANDING_ROUTE_MAP[role] || 'access-restricted'
}

function getDashboardNavItemsForUser(user) {
  if (!user || !isUserApproved(user) || !isDashboardRole(user.role)) {
    return []
  }

  const items = DASHBOARD_NAV_ITEMS.filter((item) => item.allowRoles.includes(user.role))
  if (isPersonalWorkspaceUser(user)) {
    return items.filter((item) => item.key === 'cases')
  }
  return items
}

export function getVisibleNavItems(user) {
  return getDashboardNavItemsForUser(user)
}

export function getDefaultRouteName(user) {
  if (!user) {
    return 'login'
  }
  if (!isUserApproved(user)) {
    return 'pending-approval'
  }
  if (isPersonalWorkspaceUser(user)) {
    return 'cases'
  }
  return getRoleLandingRouteName(user.role)
}

export function isRouteAllowedForUser(user, to) {
  if (to.meta?.public) {
    return true
  }
  if (!user) {
    return false
  }

  const landing = getDefaultRouteName(user)
  if (isRestrictedLandingRouteName(landing)) {
    return to.name === landing
  }

  if (BLOCKED_PAGE_NAMES.includes(to.name)) {
    return false
  }

  if (isPersonalWorkspaceUser(user) && !PERSONAL_WORKSPACE_ALLOWED_ROUTE_NAMES.has(to.name)) {
    return false
  }

  const matchedRoleGuards = to.matched
    .map((record) => record.meta?.allowRoles)
    .filter((roles) => Array.isArray(roles) && roles.length > 0)

  if (matchedRoleGuards.length === 0) {
    return true
  }

  return matchedRoleGuards.every((allowRoles) => allowRoles.includes(user.role))
}

export function getUnauthorizedFallbackRouteName(user) {
  const landing = getDefaultRouteName(user)
  if (isRestrictedLandingRouteName(landing)) {
    return landing
  }
  if (isPersonalWorkspaceUser(user)) {
    return 'cases'
  }
  return landing || 'overview'
}
