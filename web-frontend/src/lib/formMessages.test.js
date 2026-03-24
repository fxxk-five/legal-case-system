import { describe, expect, it } from 'vitest'

import {
  validatePassword,
  validatePhone,
  validateSmsCode,
  validateTenantCode,
} from './formMessages'

describe('formMessages validators', () => {
  it('validates mainland China phone numbers', () => {
    expect(validatePhone('13800138000')).toBe('')
    expect(validatePhone('')).not.toBe('')
    expect(validatePhone('123456')).not.toBe('')
  })

  it('validates sms codes as 6 digits', () => {
    expect(validateSmsCode('123456')).toBe('')
    expect(validateSmsCode('12345')).not.toBe('')
    expect(validateSmsCode('abc123')).not.toBe('')
  })

  it('validates password complexity and length', () => {
    expect(validatePassword('Passw0rd')).toBe('')
    expect(validatePassword('short1')).not.toBe('')
    expect(validatePassword('passwordonly')).not.toBe('')
    expect(validatePassword('12345678')).not.toBe('')
  })

  it('validates tenant codes when provided', () => {
    expect(validateTenantCode('', { required: false })).toBe('')
    expect(validateTenantCode('', { required: true })).not.toBe('')
    expect(validateTenantCode('tenant_01')).toBe('')
    expect(validateTenantCode('ABCD')).not.toBe('')
  })
})
