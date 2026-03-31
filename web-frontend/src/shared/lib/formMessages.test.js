import { describe, expect, it } from 'vitest'

import {
  extractFriendlyError,
  getErrorMessageByCode,
  resolveFriendlyErrorFromPayload,
  validatePassword,
  validatePhone,
  validateSmsCode,
  validateTenantCode,
} from './formMessages'

describe('formMessages validators', () => {
  it('validates mainland China phone numbers', () => {
    expect(validatePhone('13800138000')).toBe('')
    expect(validatePhone('')).toBe('请输入手机号。')
    expect(validatePhone('123456')).toBe('手机号格式不正确，应为 11 位中国大陆手机号。')
  })

  it('validates sms codes as 6 digits', () => {
    expect(validateSmsCode('123456')).toBe('')
    expect(validateSmsCode('12345')).toBe('验证码必须为 6 位数字。')
    expect(validateSmsCode('abc123')).toBe('验证码必须为 6 位数字。')
  })

  it('validates password complexity and length', () => {
    expect(validatePassword('Passw0rd')).toBe('')
    expect(validatePassword('short1')).toBe('密码至少需要 8 位。')
    expect(validatePassword('passwordonly')).toBe('密码必须同时包含字母和数字。')
    expect(validatePassword('12345678')).toBe('密码必须同时包含字母和数字。')
  })

  it('validates tenant codes when provided', () => {
    expect(validateTenantCode('', { required: false })).toBe('')
    expect(validateTenantCode('', { required: true })).toBe('请输入租户编码。')
    expect(validateTenantCode('tenant_01')).toBe('')
    expect(validateTenantCode('ABCD')).toBe('租户编码只能使用小写字母、数字、下划线和中划线。')
  })
})

describe('friendly error resolution', () => {
  it('maps domain error codes before raw backend messages', () => {
    expect(getErrorMessageByCode('FILE_TOKEN_INVALID')).toBe('文件访问链接无效或已过期。')
    expect(
      resolveFriendlyErrorFromPayload(
        {
          code: 'FILE_TOKEN_INVALID',
          message: 'raw backend message',
          detail: 'raw backend detail',
        },
        'fallback',
        403,
      ),
    ).toBe('文件访问链接无效或已过期。')
  })

  it('renders validation issue arrays as joined messages', () => {
    const message = resolveFriendlyErrorFromPayload(
      {
        detail: [
          { loc: ['body', 'phone'], type: 'missing' },
          { loc: ['body', 'password'], type: 'string_too_short', ctx: { min_length: 8 } },
        ],
      },
      'fallback',
      422,
    )

    expect(message).toContain('手机号')
    expect(message).toContain('密码')
  })

  it('prefers interceptor-computed userMessage when present', () => {
    expect(
      extractFriendlyError(
        {
          userMessage: '已使用拦截器统一错误提示。',
          isAxiosError: true,
        },
        'fallback',
      ),
    ).toBe('已使用拦截器统一错误提示。')
  })
})
