import { describe, expect, it } from 'vitest'

import {
  CLIENT_CASE_LIST_PAGE,
  FORCE_RESET_PASSWORD_PAGE,
  getClientAccessResult,
  getWorkspaceAccessResult,
  resolveUserHomeUrl,
} from '../../../../../mini-program/features/auth/role-routing.js'

describe('mini-program role routing (force reset password)', () => {
  it('redirects user home to force-reset page when must_reset_password is true', () => {
    const nextUrl = resolveUserHomeUrl({
      role: 'lawyer',
      status: 1,
      must_reset_password: true,
      tenant_type: 'organization',
    })

    expect(nextUrl).toBe(FORCE_RESET_PASSWORD_PAGE)
  })

  it('blocks workspace access before password reset is completed', () => {
    const result = getWorkspaceAccessResult({
      role: 'tenant_admin',
      status: 1,
      must_reset_password: true,
    })

    expect(result.ok).toBe(false)
    expect(result.message).toContain('先修改密码')
  })

  it('blocks client access before password reset is completed', () => {
    const result = getClientAccessResult({
      role: 'client',
      status: 1,
      must_reset_password: true,
    })

    expect(result.ok).toBe(false)
    expect(result.message).toContain('先修改密码')
  })

  it('returns client workspace routes again after password reset is completed', () => {
    const caseDetailUrl = resolveUserHomeUrl(
      {
        role: 'client',
        status: 1,
        must_reset_password: false,
      },
      [{ id: 12 }],
    )
    const listUrl = resolveUserHomeUrl({
      role: 'client',
      status: 1,
      must_reset_password: false,
    })

    expect(caseDetailUrl).toContain('/pages/client/case-detail')
    expect(listUrl).toBe(CLIENT_CASE_LIST_PAGE)
  })
})
