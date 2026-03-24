export const ROLE_LABELS = {
  super_admin: "\u8d85\u7ea7\u7ba1\u7406\u5458",
  tenant_admin: "\u673a\u6784\u7ba1\u7406\u5458",
  lawyer: "\u5f8b\u5e08",
  org_lawyer: "\u673a\u6784\u5f8b\u5e08",
  solo_lawyer: "\u72ec\u7acb\u5f8b\u5e08",
  client: "\u5f53\u4e8b\u4eba",
};

export const CASE_STATUS_OPTIONS = [
  { value: "", label: "\u5168\u90e8\u72b6\u6001" },
  { value: "new", label: "\u65b0\u5efa" },
  { value: "processing", label: "\u5904\u7406\u4e2d" },
  { value: "done", label: "\u5df2\u5b8c\u6210" },
];

export const LEGAL_TYPE_OPTIONS = [
  { value: "", label: "\u5168\u90e8\u6cd5\u5f8b\u7c7b\u578b" },
  { value: "civil_loan", label: "\u6c11\u95f4\u501f\u8d37" },
  { value: "labor_dispute", label: "\u52b3\u52a8\u4e89\u8bae" },
  { value: "contract_dispute", label: "\u5408\u540c\u7ea0\u7eb7" },
  { value: "marriage_family", label: "\u5a5a\u59fb\u5bb6\u4e8b" },
  { value: "traffic_accident", label: "\u4ea4\u901a\u4e8b\u6545" },
  { value: "criminal_defense", label: "\u5211\u4e8b\u8fa9\u62a4" },
  { value: "other", label: "\u5176\u4ed6" },
];

export const CASE_SORT_OPTIONS = [
  { value: "created_at_desc", label: "\u521b\u5efa\u65f6\u95f4\uff1a\u6700\u65b0\u4f18\u5148" },
  { value: "created_at_asc", label: "\u521b\u5efa\u65f6\u95f4\uff1a\u6700\u65e9\u4f18\u5148" },
  { value: "updated_at_desc", label: "\u66f4\u65b0\u65f6\u95f4\uff1a\u6700\u65b0\u4f18\u5148" },
  { value: "updated_at_asc", label: "\u66f4\u65b0\u65f6\u95f4\uff1a\u6700\u65e9\u4f18\u5148" },
  { value: "deadline_asc", label: "\u622a\u6b62\u65f6\u95f4\uff1a\u6700\u8fd1\u4f18\u5148" },
  { value: "deadline_desc", label: "\u622a\u6b62\u65f6\u95f4\uff1a\u6700\u8fdc\u4f18\u5148" },
  { value: "legal_type_asc", label: "\u6cd5\u5f8b\u7c7b\u578b\uff1aA-Z" },
  { value: "legal_type_desc", label: "\u6cd5\u5f8b\u7c7b\u578b\uff1aZ-A" },
];

const CASE_STATUS_LABELS = {
  new: "\u65b0\u5efa",
  processing: "\u5904\u7406\u4e2d",
  done: "\u5df2\u5b8c\u6210",
};

const LEGAL_TYPE_LABELS = LEGAL_TYPE_OPTIONS.reduce((accumulator, item) => {
  if (item.value) {
    accumulator[item.value] = item.label;
  }
  return accumulator;
}, {});

const TENANT_TYPE_LABELS = {
  personal: "\u4e2a\u4eba\u7a7a\u95f4",
  organization: "\u673a\u6784\u7a7a\u95f4",
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
  return ROLE_LABELS[role] || role || "\u672a\u8bbe\u7f6e";
}

export function formatCaseStatus(status) {
  return CASE_STATUS_LABELS[status] || status || "\u672a\u8bbe\u7f6e";
}

export function formatLegalType(legalType) {
  return LEGAL_TYPE_LABELS[legalType] || legalType || "\u672a\u8bbe\u7f6e";
}

export function formatTenantType(type) {
  return TENANT_TYPE_LABELS[type] || type || "\u672a\u8bbe\u7f6e";
}

export function formatText(value, fallback = "\u672a\u586b\u5199") {
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
    not_started: "\u672a\u89e3\u6790",
    queued: `\u6392\u961f\u4e2d ${percent}%`,
    pending: `\u6392\u961f\u4e2d ${percent}%`,
    pending_reanalysis: "\u5f85\u91cd\u65b0\u89e3\u6790",
    processing: `\u89e3\u6790\u4e2d ${percent}%`,
    completed: "\u89e3\u6790\u5b8c\u6210",
    failed: "\u89e3\u6790\u5931\u8d25",
    dead: "\u89e3\u6790\u5931\u8d25",
  };

  return map[normalized] || status || "\u672a\u89e3\u6790";
}

export function getDeadlineReminder(caseItem = {}) {
  if (String(caseItem.status || "") === "done") {
    return {
      text: "\u5df2\u7ed3\u6848",
      tone: "success",
      style: "color:#166534;background:#dcfce7;",
    };
  }

  if (!caseItem.deadline) {
    return {
      text: "\u672a\u8bbe\u7f6e\u622a\u6b62\u65f6\u95f4",
      tone: "neutral",
      style: "color:#475569;background:#e2e8f0;",
    };
  }

  const deadline = new Date(caseItem.deadline);
  if (Number.isNaN(deadline.getTime())) {
    return {
      text: "\u622a\u6b62\u65f6\u95f4\u5f85\u786e\u8ba4",
      tone: "neutral",
      style: "color:#475569;background:#e2e8f0;",
    };
  }

  const diffMs = deadline.getTime() - Date.now();
  const diffDays = Math.ceil(diffMs / (24 * 60 * 60 * 1000));

  if (diffDays < 0) {
    return {
      text: `\u5df2\u903e\u671f ${Math.abs(diffDays)} \u5929`,
      tone: "danger",
      style: "color:#991b1b;background:#fee2e2;",
    };
  }

  if (diffDays <= 7) {
    return {
      text: `${diffDays} \u5929\u5185\u5230\u671f`,
      tone: "danger",
      style: "color:#991b1b;background:#fee2e2;",
    };
  }

  if (diffDays <= 30) {
    return {
      text: `${diffDays} \u5929\u5185\u5230\u671f`,
      tone: "warning",
      style: "color:#92400e;background:#fef3c7;",
    };
  }

  return {
    text: "\u8fdb\u5ea6\u6b63\u5e38",
    tone: "neutral",
    style: "color:#0f766e;background:#ccfbf1;",
  };
}
