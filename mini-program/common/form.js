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
  USER_NOT_ACTIVE: '账号待审批或已禁用，请联系管理员。',

  TENANT_NOT_FOUND: '机构不存在。',
  TENANT_INACTIVE: '机构未启用，请联系管理员。',

  INVITE_NOT_FOUND: '邀请链接不存在。',
  INVITE_EXPIRED: '邀请链接已过期。',
  INVITE_INVALID: '邀请链接无效。',
  INVITE_REQUIRED: '当前注册需使用邀请链接。',
  PHONE_NOT_VERIFIED: '手机号未完成验证，请先校验验证码。',
  SMS_CODE_RATE_LIMITED: '验证码发送过于频繁，请稍后再试。',
  SMS_CODE_INVALID: '验证码错误，请重新输入。',
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
  if (!text) return `请输入${label}`
  if (!/^1[3-9]\d{9}$/.test(text)) return `${label}应为 11 位中国大陆手机号`
  return ''
}

export function validateSmsCode(value, label = '验证码') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}`
  if (!/^\d{6}$/.test(text)) return `${label}应为 6 位数字`
  return ''
}

export function validatePassword(value, label = '密码', required = true) {
  const text = String(value || '')
  if (!text) return required ? `请输入${label}` : ''
  if (text.length < 8) return `${label}至少需要 8 位`
  if (text.length > 128) return `${label}不能超过 128 位`
  return ''
}

export function validateName(value, label = '姓名') {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}`
  if (text.length > 100) return `${label}不能超过 100 个字符`
  return ''
}

export function validateTenantCode(value, required = false) {
  const text = String(value || '').trim()
  if (!text) return required ? '请输入租户编码' : ''
  if (text.length < 3) return '租户编码至少需要 3 个字符'
  if (text.length > 50) return '租户编码不能超过 50 个字符'
  if (!/^[a-zA-Z0-9-]+$/.test(text)) return '租户编码只能使用字母、数字和中划线'
  return ''
}

export function validateTitle(value, label = '标题', maxLength = 255) {
  const text = String(value || '').trim()
  if (!text) return `请输入${label}`
  if (text.length > maxLength) return `${label}不能超过 ${maxLength} 个字符`
  return ''
}

function mapLocToLabel(loc = []) {
  const field = loc[loc.length - 1]
  const fieldMap = {
    phone: '手机号',
    password: '密码',
    code: '验证码',
    real_name: '姓名',
    tenant_code: '租户编码',
    title: '标题',
    case_number: '案号',
    legal_type: '法律类型',
    client_phone: '当事人手机号',
    client_real_name: '当事人姓名',
    file_name: '文件名',
    content_type: '文件类型',
    phone_verification_token: '验证码校验凭证',
    token: '邀请链接',
  }
  return fieldMap[field] || '输入内容'
}

function mapValidationIssue(issue) {
  const label = mapLocToLabel(issue.loc)
  if (issue.type === 'string_too_short') {
    return `${label}至少需要 ${issue.ctx && issue.ctx.min_length ? issue.ctx.min_length : 1} 个字符`
  }
  if (issue.type === 'string_too_long') {
    return `${label}不能超过 ${issue.ctx && issue.ctx.max_length ? issue.ctx.max_length : 0} 个字符`
  }
  if (issue.type === 'string_pattern_mismatch') {
    return `${label}格式不正确`
  }
  if (issue.type === 'missing') {
    return `${label}不能为空`
  }
  return issue.msg ? `${label}${issue.msg}` : `${label}填写不正确`
}

function mapCodeToMessage(code) {
  if (!code || typeof code !== 'string') {
    return ''
  }
  return ERROR_CODE_MESSAGES[code] || ''
}

export function friendlyError(error, fallback = '操作失败') {
  const codeMessage = mapCodeToMessage(error && error.code)
  if (codeMessage) {
    return codeMessage
  }

  const detail = error && error.detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map(mapValidationIssue).join('；')
  }

  if (error && typeof error.message === 'string' && error.message.trim()) {
    return error.message
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (error && typeof error.errMsg === 'string' && error.errMsg.trim()) {
    if (error.errMsg.includes('request:fail')) {
      return '网络连接失败，请确认后端服务已启动并重试'
    }
    if (error.errMsg.includes('uploadFile:fail')) {
      return '文件上传失败，请稍后重试'
    }
    if (error.errMsg.includes('downloadFile:fail')) {
      return '文件下载失败，请稍后重试'
    }
    if (error.errMsg.includes('openDocument:fail')) {
      return '文件预览失败，请确认文件格式是否受支持'
    }
    return error.errMsg
  }

  if (typeof error === 'string' && error.trim()) {
    return error
  }

  return fallback
}

export function showFormError(message) {
  uni.showToast({ title: message, icon: 'none' })
}
