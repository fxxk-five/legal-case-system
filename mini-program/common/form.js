export function validatePhone(value, label = "手机号") {
  const text = String(value || "").trim();
  if (!text) return `请输入${label}`;
  if (!/^\d{6,20}$/.test(text)) return `${label}应为 6 到 20 位数字`;
  return "";
}

export function validatePassword(value, label = "密码", required = true) {
  const text = String(value || "");
  if (!text) return required ? `请输入${label}` : "";
  if (text.length < 6) return `${label}至少需要 6 位`;
  if (text.length > 128) return `${label}不能超过 128 位`;
  return "";
}

export function validateName(value, label = "姓名") {
  const text = String(value || "").trim();
  if (!text) return `请输入${label}`;
  if (text.length > 100) return `${label}不能超过 100 个字符`;
  return "";
}

export function validateTenantCode(value, required = false) {
  const text = String(value || "").trim();
  if (!text) return required ? "请输入租户编码" : "";
  if (text.length < 3) return "租户编码至少需要 3 个字符";
  if (text.length > 50) return "租户编码不能超过 50 个字符";
  if (!/^[a-zA-Z0-9-]+$/.test(text)) return "租户编码只能使用字母、数字和中划线";
  return "";
}

export function validateTitle(value, label = "标题", maxLength = 255) {
  const text = String(value || "").trim();
  if (!text) return `请输入${label}`;
  if (text.length > maxLength) return `${label}不能超过 ${maxLength} 个字符`;
  return "";
}

function mapLocToLabel(loc = []) {
  const field = loc[loc.length - 1];
  const fieldMap = {
    phone: "手机号",
    password: "密码",
    real_name: "姓名",
    tenant_code: "租户编码",
    title: "标题",
    case_number: "案号",
    client_phone: "当事人手机号",
    client_real_name: "当事人姓名",
  };
  return fieldMap[field] || "输入内容";
}

export function friendlyError(error, fallback = "操作失败") {
  const detail = error && error.detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => {
        const label = mapLocToLabel(item.loc);
        if (item.type === "string_too_short") {
          return `${label}至少需要 ${item.ctx && item.ctx.min_length ? item.ctx.min_length : 1} 个字符`;
        }
        if (item.type === "string_too_long") {
          return `${label}不能超过 ${item.ctx && item.ctx.max_length ? item.ctx.max_length : 0} 个字符`;
        }
        if (item.type === "string_pattern_mismatch") {
          return `${label}格式不正确`;
        }
        return item.msg ? `${label}${item.msg}` : `${label}填写不正确`;
      })
      .join("；");
  }
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (typeof error === "string" && error.trim()) {
    return error;
  }
  return fallback;
}

export function showFormError(message) {
  uni.showToast({ title: message, icon: "none" });
}
