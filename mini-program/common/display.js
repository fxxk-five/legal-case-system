const caseStatusMap = {
  new: "新建",
  processing: "处理中",
  done: "已完成",
};

export function formatCaseStatus(status) {
  return caseStatusMap[status] || status || "未设置";
}

export function formatText(value, fallback = "未填写") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return value;
}
