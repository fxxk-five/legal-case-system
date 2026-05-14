import {
  buildQuery,
  del,
  get,
  getAnalysisResults,
  getTaskStatus,
  patch,
  retryTask,
  upload,
} from "./http";

const FIELD_LABELS = {
  caseId: "案件参数",
  fileId: "文件参数",
  taskId: "任务参数",
};

function createClientValidationError(message, code = "VALIDATION_ERROR") {
  return {
    code,
    message,
    detail: message,
    status_code: 400,
    userMessage: message,
  };
}

function normalizeNumericId(value, fieldName) {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    const fieldLabel = FIELD_LABELS[fieldName] || "请求参数";
    throw createClientValidationError(`${fieldLabel}无效，请稍后重试。`);
  }
  return parsed;
}

function normalizeRemarkText(value) {
  return String(value === null || value === undefined ? "" : value).trim();
}

export const casesApi = {
  listCases() {
    return get("/cases");
  },
  getCaseDetail(caseId) {
    return get(`/cases/${normalizeNumericId(caseId, "caseId")}`);
  },
  updateCaseStatus(caseId, status) {
    return patch(`/cases/${normalizeNumericId(caseId, "caseId")}`, { status });
  },
  getCaseInviteQrcode(caseId) {
    return get(`/cases/${normalizeNumericId(caseId, "caseId")}/invite-qrcode`);
  },
  getLatestReportAccessLink(caseId) {
    return get(`/cases/${normalizeNumericId(caseId, "caseId")}/report/access-link`);
  },
  getReportVersionAccessLink(caseId, reportName) {
    const safeReportName = encodeURIComponent(String(reportName || "").trim());
    return get(`/cases/${normalizeNumericId(caseId, "caseId")}/reports/${safeReportName}/access-link`);
  },
};

export const filesApi = {
  listCaseFiles(caseId) {
    return get(`/files/case/${normalizeNumericId(caseId, "caseId")}`);
  },
  getFileAccessLink(fileId) {
    return get(`/files/${normalizeNumericId(fileId, "fileId")}/access-link`);
  },
  deleteFile(fileId) {
    return del(`/files/${normalizeNumericId(fileId, "fileId")}`);
  },
  uploadCaseFile({ caseId, filePath, description = "", onProgress } = {}) {
    if (!filePath) {
      throw createClientValidationError("请选择要上传的文件。", "FILE_UPLOAD_INVALID");
    }
    const query = description ? `?description=${encodeURIComponent(String(description || "").trim())}` : "";
    return upload(`/cases/${normalizeNumericId(caseId, "caseId")}/files${query}`, filePath, "upload", {}, { onProgress });
  },
};

export const remarksApi = {
  updateClientRemark(caseId, remark) {
    return patch(`/cases/${normalizeNumericId(caseId, "caseId")}/client-remark`, {
      client_remark: normalizeRemarkText(remark),
    });
  },
  updateLawyerRemark(caseId, remark) {
    return patch(`/cases/${normalizeNumericId(caseId, "caseId")}/lawyer-remark`, {
      lawyer_remark: normalizeRemarkText(remark),
    });
  },
  async transcribeCaseRemarkAudio(filePath) {
    if (!filePath) {
      throw { message: "录音文件不存在，请重新录制" };
    }

    try {
      const data = await upload("/asr/transcribe", filePath, "audio");
      const text = normalizeRemarkText(data?.text || data?.result || data?.transcript);
      if (!text) {
        throw { message: "未识别到有效内容，请重试或改用文字输入" };
      }
      return text;
    } catch (error) {
      if (Number(error?.status_code) === 404) {
        throw {
          ...error,
          message: "语音识别服务暂未开启，请先使用文字输入",
        };
      }
      throw error;
    }
  },
  getRemarkValue(payload, field, fallback = "") {
    if (payload && typeof payload[field] === "string") {
      return payload[field];
    }
    return fallback;
  },
  appendClientRemarkPreview(existingRemark, latestRemark) {
    const previous = normalizeRemarkText(existingRemark);
    const next = normalizeRemarkText(latestRemark);
    if (!next) {
      return previous;
    }
    return previous ? `${previous}\n\n${next}` : next;
  },
};

export const aiTasksApi = {
  listTasks(params = {}) {
    return get(`/ai/tasks${buildQuery(params)}`);
  },
  getTaskStatus(taskId) {
    return getTaskStatus(taskId);
  },
  retryTask(taskId, reason = "") {
    return retryTask(taskId, reason);
  },
  getCaseAnalysisResults(caseId) {
    return getAnalysisResults(normalizeNumericId(caseId, "caseId"));
  },
};
