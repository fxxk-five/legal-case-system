export const ROLE_LABELS = {
  super_admin: "超级管理员",
  tenant_admin: "机构管理员",
  lawyer: "律师",
  org_lawyer: "机构律师",
  solo_lawyer: "独立律师",
  client: "当事人",
};

export const CASE_STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "new", label: "待上传材料" },
  { value: "processing", label: "律师整理中" },
  { value: "done", label: "分析完成" },
];

export const LEGAL_TYPE_OPTIONS = [
  { value: "", label: "全部法律类型" },
  { value: "civil_loan", label: "民间借贷" },
  { value: "labor_dispute", label: "劳动争议" },
  { value: "contract_dispute", label: "合同纠纷" },
  { value: "marriage_family", label: "婚姻家事" },
  { value: "traffic_accident", label: "交通事故" },
  { value: "criminal_defense", label: "刑事辩护" },
  { value: "other", label: "其他" },
];

export const CASE_SORT_OPTIONS = [
  { value: "created_at_desc", label: "创建时间：最新优先" },
  { value: "created_at_asc", label: "创建时间：最早优先" },
  { value: "updated_at_desc", label: "更新时间：最新优先" },
  { value: "updated_at_asc", label: "更新时间：最早优先" },
  { value: "deadline_asc", label: "截止时间：最近优先" },
  { value: "deadline_desc", label: "截止时间：最远优先" },
  { value: "legal_type_asc", label: "法律类型：A-Z" },
  { value: "legal_type_desc", label: "法律类型：Z-A" },
];

const CASE_STATUS_LABELS = {
  new: "待上传材料",
  processing: "律师整理中",
  done: "分析完成",
};

const LEGAL_TYPE_LABELS = LEGAL_TYPE_OPTIONS.reduce((accumulator, item) => {
  if (item.value) {
    accumulator[item.value] = item.label;
  }
  return accumulator;
}, {});

const TENANT_TYPE_LABELS = {
  personal: "个人空间",
  organization: "机构空间",
};

export function normalizeRole(role) {
  if (role === "org_lawyer" || role === "solo_lawyer") {
    return "lawyer";
  }
  return role || "";
}

export function isWorkspaceRole(userOrRole) {
  const role = normalizeRole(typeof userOrRole === "object" ? userOrRole && userOrRole.role : userOrRole);
  return ["tenant_admin", "lawyer"].includes(role || "");
}

export function isTenantAdmin(userOrRole) {
  if (typeof userOrRole === "object" && userOrRole) {
    return Boolean(userOrRole.is_tenant_admin) || normalizeRole(userOrRole.role) === "tenant_admin";
  }
  return normalizeRole(userOrRole) === "tenant_admin";
}

export function isUserApproved(user) {
  return Number(user?.status) === 1;
}

export function isAccessRestrictedRole(userOrRole) {
  const role = normalizeRole(typeof userOrRole === "object" ? userOrRole && userOrRole.role : userOrRole);
  return role === "super_admin";
}

export function formatRole(role) {
  return ROLE_LABELS[role] || role || "未设置";
}

export function formatCaseStatus(status) {
  return CASE_STATUS_LABELS[status] || status || "未设置";
}

export function formatLegalType(legalType) {
  return LEGAL_TYPE_LABELS[legalType] || legalType || "未设置";
}

export function formatTenantType(type) {
  return TENANT_TYPE_LABELS[type] || type || "未设置";
}

export function formatText(value, fallback = "未填写") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return value;
}

export function formatDateTime(value, fallback = "-") {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).replace("T", " ").slice(0, 19) || fallback;
  }

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatShortDateTime(value, fallback = "-") {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).replace("T", " ").slice(5, 16) || fallback;
  }

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatAnalysisStatus(status, progress) {
  const normalized = String(status || "").toLowerCase();
  const percent = Math.max(0, Math.min(100, Number(progress || 0)));

  const map = {
    not_started: "未解析",
    queued: `排队中 ${percent}%`,
    pending: `排队中 ${percent}%`,
    pending_reanalysis: "待重新解析",
    processing: `解析中 ${percent}%`,
    completed: "解析完成",
    failed: "解析失败",
    dead: "解析失败",
  };

  return map[normalized] || status || "未解析";
}

export function getDeadlineReminder(caseItem = {}) {
  if (String(caseItem.status || "") === "done") {
    return {
      text: "已结案",
      tone: "success",
      style: "color:#166534;background:#dcfce7;",
    };
  }

  if (!caseItem.deadline) {
    return {
      text: "未设置截止时间",
      tone: "neutral",
      style: "color:#475569;background:#e2e8f0;",
    };
  }

  const deadline = new Date(caseItem.deadline);
  if (Number.isNaN(deadline.getTime())) {
    return {
      text: "截止时间待确认",
      tone: "neutral",
      style: "color:#475569;background:#e2e8f0;",
    };
  }

  const diffMs = deadline.getTime() - Date.now();
  const diffDays = Math.ceil(diffMs / (24 * 60 * 60 * 1000));

  if (diffDays < 0) {
    return {
      text: `已逾期 ${Math.abs(diffDays)} 天`,
      tone: "danger",
      style: "color:#991b1b;background:#fee2e2;",
    };
  }

  if (diffDays <= 7) {
    return {
      text: `${diffDays} 天内到期`,
      tone: "danger",
      style: "color:#991b1b;background:#fee2e2;",
    };
  }

  if (diffDays <= 30) {
    return {
      text: `${diffDays} 天内到期`,
      tone: "warning",
      style: "color:#92400e;background:#fef3c7;",
    };
  }

  return {
    text: "进度正常",
    tone: "neutral",
    style: "color:#0f766e;background:#ccfbf1;",
  };
}
