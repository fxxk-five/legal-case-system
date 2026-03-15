import axios from 'axios'

export function validatePhone(value, label = '手机号') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}。`
  if (!/^\d{6,20}$/.test(text)) return `${label}应为 6 到 20 位数字。`
  return ''
}

export function validatePassword(value, label = '密码') {
  const text = String(value || '')
  if (!text) return `请输入${label}。`
  if (text.length < 6) return `${label}至少需要 6 位。`
  if (text.length > 128) return `${label}不能超过 128 位。`
  return ''
}

export function validateName(value, label = '姓名') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}。`
  if (text.length < 1) return `${label}不能为空。`
  if (text.length > 100) return `${label}不能超过 100 个字符。`
  return ''
}

export function validateTenantCode(value, { required = false, label = '租户编码' } = {}) {
  const text = String(value || '').trim()
  if (!text) return required ? `请输入${label}。` : ''
  if (text.length < 3) return `${label}至少需要 3 个字符。`
  if (text.length > 50) return `${label}不能超过 50 个字符。`
  if (!/^[a-zA-Z0-9-]+$/.test(text)) return `${label}只能使用字母、数字和中划线。`
  return ''
}

export function validateWorkspaceName(value, label = '名称') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}。`
  if (text.length > 100) return `${label}不能超过 100 个字符。`
  return ''
}

function mapLocToLabel(loc = []) {
  const field = loc[loc.length - 1]
  const fieldMap = {
    phone: '手机号',
    password: '密码',
    real_name: '姓名',
    tenant_code: '租户编码',
    workspace_name: '工作空间名称',
    admin_phone: '管理员手机号',
    admin_password: '管理员密码',
    admin_real_name: '管理员姓名',
    contact_name: '联系人',
    name: '机构名称',
    title: '标题',
    case_number: '案号',
    client_phone: '当事人手机号',
    client_real_name: '当事人姓名',
  }
  return fieldMap[field] || '输入内容'
}

function mapValidationIssue(issue) {
  const label = mapLocToLabel(issue.loc)
  if (issue.type === 'string_too_short') {
    return `${label}${issue.ctx?.min_length ? `至少需要 ${issue.ctx.min_length} 个字符` : '长度过短'}。`
  }
  if (issue.type === 'string_too_long') {
    return `${label}${issue.ctx?.max_length ? `不能超过 ${issue.ctx.max_length} 个字符` : '长度过长'}。`
  }
  if (issue.type === 'string_pattern_mismatch') {
    return `${label}格式不正确。`
  }
  if (issue.type === 'missing') {
    return `${label}不能为空。`
  }
  return `${label}${issue.msg || '填写不正确。'}`
}

export function extractFriendlyError(error, fallback) {
  if (!axios.isAxiosError(error)) return fallback

  const detail = error.response?.data?.detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map(mapValidationIssue).join(' ')
  }
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}
