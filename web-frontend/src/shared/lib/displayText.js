const roleMap = {
  super_admin: '超级管理员',
  tenant_admin: '机构管理员',
  lawyer: '律师',
  org_lawyer: '机构律师',
  solo_lawyer: '独立律师',
  client: '当事人',
}

const roleAliases = {
  org_lawyer: 'lawyer',
  solo_lawyer: 'lawyer',
}

const caseStatusMap = {
  new: '待上传材料',
  processing: '律师整理中',
  done: '分析完成',
}

const legalTypeMap = {
  civil_loan: '民间借贷',
  labor_dispute: '劳动争议',
  contract_dispute: '合同纠纷',
  marriage_family: '婚姻家事',
  traffic_accident: '交通事故',
  criminal_defense: '刑事辩护',
  other: '其他',
}

const tenantTypeMap = {
  personal: '个人空间',
  organization: '机构空间',
}

const tenantStatusMap = {
  0: '已创建',
  1: '正常',
  2: '已停用',
  3: '已归档',
  created: '已创建',
  active: '正常',
  disabled: '已停用',
  archived: '已归档',
  pending: '待审核',
}

const userStatusMap = {
  0: '待审批',
  1: '正常',
  2: '已停用',
  3: '已拒绝',
  pending: '待审批',
  active: '正常',
  disabled: '已停用',
  rejected: '已拒绝',
}

export function formatRole(role) {
  return roleMap[role] || roleMap[normalizeRole(role)] || role || '未设置'
}

export function normalizeRole(role) {
  const normalized = String(role || '').trim().toLowerCase()
  return roleAliases[normalized] || normalized
}

export function formatCaseStatus(status) {
  return caseStatusMap[status] || status || '未设置'
}

export function formatLegalType(legalType) {
  return legalTypeMap[legalType] || legalType || '未设置'
}

export function formatTenantType(type) {
  return tenantTypeMap[type] || type || '未设置'
}

export function formatTenantStatus(status) {
  return tenantStatusMap[status] || status || '未设置'
}

export function formatUserStatus(status) {
  return userStatusMap[status] || status || '未设置'
}

export function formatText(value, fallback = '未填写') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  return value
}

/**
 * 根据截止时间返回提醒级别和文字，供案件列表和详情页共用。
 * @param {string|null} deadline - ISO 日期字符串
 * @param {string} [status] - 案件状态
 * @returns {{ level: 'danger'|'warning'|'success'|'neutral', text: string }}
 */
export function getDeadlineReminder(deadline, status) {
  if (deadline) {
    const d = new Date(deadline)
    if (!Number.isNaN(d.getTime())) {
      const diffMs = d.getTime() - Date.now()
      const diffDays = Math.ceil(diffMs / (24 * 60 * 60 * 1000))
      if (diffDays < 0) return { level: 'danger', text: `已逾期 ${Math.abs(diffDays)} 天` }
      if (diffDays <= 7) return { level: 'danger', text: `${diffDays} 天内到期` }
      if (diffDays <= 30) return { level: 'warning', text: `${diffDays} 天内到期` }
      return { level: 'neutral', text: '进度正常' }
    }
  }
  if (status === 'done' || status === 'closed' || status === 'archived') {
    return { level: 'success', text: '已结案' }
  }
  return { level: 'neutral', text: '未设截止' }
}
