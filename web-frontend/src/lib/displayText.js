const roleMap = {
  super_admin: '超级管理员',
  tenant_admin: '机构管理员',
  lawyer: '律师',
  client: '当事人',
}

const caseStatusMap = {
  new: '新建',
  processing: '处理中',
  done: '已完成',
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
  return roleMap[role] || role || '未设置'
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
