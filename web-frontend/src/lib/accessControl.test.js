import { describe, expect, it } from 'vitest'

import {
  getDefaultRouteName,
  getUnauthorizedFallbackRouteName,
  getVisibleNavItems,
  isRouteAllowedForUser,
} from './accessControl'

function buildRoute(name, allowRoles = null, isPublic = false) {
  return {
    name,
    meta: {
      public: isPublic,
    },
    matched: allowRoles ? [{ meta: { allowRoles } }] : [],
  }
}

describe('accessControl', () => {
  it('returns role-aware default routes', () => {
    expect(getDefaultRouteName(null)).toBe('login')
    expect(getDefaultRouteName({ role: 'lawyer', status: 0 })).toBe('pending-approval')
    expect(getDefaultRouteName({ role: 'lawyer', status: 1 })).toBe('overview')
    expect(getDefaultRouteName({ role: 'lawyer', status: 1, tenant_type: 'personal' })).toBe('cases')
    expect(getDefaultRouteName({ role: 'client', status: 1 })).toBe('client-mini-only')
  })

  it('filters visible navigation items by approved role', () => {
    expect(getVisibleNavItems({ role: 'tenant_admin', status: 1 }).map((item) => item.key)).toEqual([
      'overview',
      'cases',
      'clients',
      'lawyers',
    ])
    expect(getVisibleNavItems({ role: 'lawyer', status: 1 }).map((item) => item.key)).toEqual([
      'overview',
      'cases',
      'clients',
    ])
    expect(
      getVisibleNavItems({ role: 'lawyer', status: 1, tenant_type: 'personal' }).map((item) => item.key),
    ).toEqual(['cases'])
    expect(getVisibleNavItems({ role: 'client', status: 1 })).toEqual([])
  })

  it('allows and blocks routes according to landing page and role guards', () => {
    const publicRoute = buildRoute('login', null, true)
    const overviewRoute = buildRoute('overview', ['tenant_admin', 'lawyer'])
    const casesRoute = buildRoute('cases', ['tenant_admin', 'lawyer'])
    const caseDetailRoute = buildRoute('case-detail', ['tenant_admin', 'lawyer'])
    const clientsRoute = buildRoute('clients', ['tenant_admin', 'lawyer'])
    const lawyersRoute = buildRoute('lawyers', ['tenant_admin'])

    expect(isRouteAllowedForUser(null, publicRoute)).toBe(true)
    expect(isRouteAllowedForUser(null, overviewRoute)).toBe(false)
    expect(isRouteAllowedForUser({ role: 'client', status: 1 }, buildRoute('client-mini-only'))).toBe(true)
    expect(isRouteAllowedForUser({ role: 'client', status: 1 }, overviewRoute)).toBe(false)
    expect(isRouteAllowedForUser({ role: 'lawyer', status: 1 }, overviewRoute)).toBe(true)
    expect(isRouteAllowedForUser({ role: 'lawyer', status: 1 }, lawyersRoute)).toBe(false)
    expect(
      isRouteAllowedForUser({ role: 'lawyer', status: 1, tenant_type: 'personal' }, casesRoute),
    ).toBe(true)
    expect(
      isRouteAllowedForUser({ role: 'lawyer', status: 1, tenant_type: 'personal' }, caseDetailRoute),
    ).toBe(true)
    expect(
      isRouteAllowedForUser({ role: 'lawyer', status: 1, tenant_type: 'personal' }, overviewRoute),
    ).toBe(false)
    expect(
      isRouteAllowedForUser({ role: 'lawyer', status: 1, tenant_type: 'personal' }, clientsRoute),
    ).toBe(false)
  })

  it('returns a safe fallback route when access is denied', () => {
    expect(getUnauthorizedFallbackRouteName({ role: 'tenant_admin', status: 1 })).toBe('overview')
    expect(getUnauthorizedFallbackRouteName({ role: 'lawyer', status: 1, tenant_type: 'personal' })).toBe(
      'cases',
    )
    expect(getUnauthorizedFallbackRouteName({ role: 'client', status: 1 })).toBe('client-mini-only')
  })
})
