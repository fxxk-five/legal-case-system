import axios from 'axios'

const STATUS_CODE_MESSAGES = {
  400: '提交信息有误，请检查后重试。',
  401: '登录已失效，请重新登录。',
  403: '无权限执行该操作。',
  404: '请求的资源不存在。',
  409: '请求冲突，请刷新后重试。',
  413: '上传文件过大，请压缩后重试。',
  415: '文件格式不受支持，请更换文件后重试。',
  422: '提交信息有误，请检查后重试。',
  500: '服务器繁忙，请稍后重试。',
  502: '外部服务暂时不可用，请稍后重试。',
  503: '外部服务暂时不可用，请稍后重试。',
  504: '外部服务暂时不可用，请稍后重试。',
}

const ERROR_CODE_MESSAGES = {
  AUTH_REQUIRED: '登录已失效，请重新登录。',
  FORBIDDEN: '无权限执行该操作。',
  TENANT_ACCESS_DENIED: '无权限访问当前机构资源。',

  CASE_NOT_FOUND: '案件不存在或已删除。',
  CASE_ACCESS_DENIED: '无权访问该案件。',
  CASE_OPERATION_NOT_ALLOWED: '当前状态不允许执行该操作。',

  FILE_NOT_FOUND: '文件不存在或已删除。',
  FILE_ACCESS_DENIED: '无权访问该文件。',
  FILE_TOKEN_INVALID: '文件访问链接无效或已过期。',
  FILE_UPLOAD_INVALID: '上传参数无效，请检查后重试。',

  USER_NOT_FOUND: '用户不存在。',
  USER_ALREADY_EXISTS: '用户已存在，请勿重复创建。',
  USER_NOT_ACTIVE: '用户未激活或已禁用。',

  TENANT_NOT_FOUND: '机构不存在。',
  TENANT_INACTIVE: '机构未启用，请联系管理员。',

  INVITE_NOT_FOUND: '邀请链接不存在。',
  INVITE_EXPIRED: '邀请链接已过期。',
  INVITE_INVALID: '邀请链接无效。',
  INVITE_REQUIRED: '机构律师必须通过邀请链接注册。',
  PHONE_NOT_VERIFIED: '请先完成短信验证码校验。',
  SMS_CODE_RATE_LIMITED: '验证码发送过于频繁，请稍后重试。',
  SMS_CODE_INVALID: '验证码错误，请检查后重试。',
  SMS_CODE_EXPIRED: '验证码已失效，请重新获取。',
  NOTIFICATION_NOT_FOUND: '通知不存在或已删除。',

  AI_TASK_NOT_FOUND: 'AI任务不存在或已结束。',
  AI_ANALYSIS_NOT_FOUND: 'AI分析结果不存在。',
  AI_OPERATION_NOT_ALLOWED: '当前角色无权执行该AI操作。',
  AI_TASK_CONFLICT: '当前任务冲突，请稍后重试。',
  AI_PROVIDER_ERROR: 'AI服务暂时不可用，请稍后重试。',

  VALIDATION_ERROR: '提交信息有误，请检查后重试。',
  CONFLICT: '请求冲突，请刷新后重试。',
  EXTERNAL_SERVICE_ERROR: '外部服务暂时不可用，请稍后重试。',
  INTERNAL_ERROR: '服务器繁忙，请稍后重试。',
}

export function validatePhone(value, label = '手机号') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}。`
  if (!/^1[3-9]\d{9}$/.test(text)) return `${label}格式不正确，应为 11 位中国大陆手机号。`
  return ''
}

export function validateSmsCode(value, label = '验证码') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}。`
  if (!/^\d{6}$/.test(text)) return `${label}必须为 6 位数字。`
  return ''
}

export function validatePassword(value, label = '密码') {
  const text = String(value || '')
  if (!text) return `请输入${label}。`
  if (text.length < 8) return `${label}至少需要 8 位。`
  if (text.length > 128) return `${label}不能超过 128 位。`
  if (/\s/.test(text)) return `${label}不能包含空格。`
  if (!/[A-Za-z]/.test(text) || !/\d/.test(text)) return `${label}必须同时包含字母和数字。`
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
  if (!/^[a-z0-9_-]+$/.test(text)) return `${label}只能使用小写字母、数字、下划线和中划线。`
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
    code: '验证码',
    token: '邀请码',
    phone_verification_token: '验证码校验凭证',
    workspace_name: '工作空间名称',
    admin_phone: '管理员手机号',
    admin_password: '管理员密码',
    admin_real_name: '管理员姓名',
    contact_name: '联系人',
    name: '机构名称',
    title: '标题',
    case_number: '案号',
    legal_type: '法律类型',
    client_phone: '当事人手机号',
    client_real_name: '当事人姓名',
    file_name: '文件名',
    content_type: '文件类型',
  }
  return fieldMap[field] || '输入内容'
}

function mapValidationIssue(issue) {
  if (!issue || typeof issue !== 'object') {
    return ''
  }

  if (typeof issue.msg === 'string' && issue.msg.trim()) {
    return issue.msg.trim()
  }

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
  return `${label}填写不正确。`
}

function mapCodeToMessage(code) {
  if (!code || typeof code !== 'string') {
    return ''
  }
  return ERROR_CODE_MESSAGES[code] || ''
}

function extractFromPayload(payload, fallback, status) {
  if (!payload || typeof payload !== 'object') {
    return STATUS_CODE_MESSAGES[status] || fallback
  }

  const codeMessage = mapCodeToMessage(payload.code)
  if (codeMessage) {
    return codeMessage
  }

  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    const detailMessage = payload.detail.map(mapValidationIssue).filter(Boolean).join('；')
    if (detailMessage) {
      return detailMessage
    }
  }

  if (typeof payload.message === 'string' && payload.message.trim()) {
    return payload.message.trim()
  }

  if (typeof payload.detail === 'string' && payload.detail.trim()) {
    return payload.detail.trim()
  }

  return STATUS_CODE_MESSAGES[status] || fallback
}

export function extractFriendlyError(error, fallback = '操作失败') {
  if (!axios.isAxiosError(error)) {
    return fallback
  }

  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return '请求超时，请稍后重试。'
    }
    return '网络连接失败，请检查服务是否可用。'
  }

  return extractFromPayload(error.response.data, fallback, error.response.status)
}
