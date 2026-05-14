import { isCaseAnalysisInProgress } from "../../entities/case/policy";

const STATUS_ALIAS = Object.freeze({
  queued: "pending",
  running: "processing",
  success: "completed",
  error: "failed",
  dead: "failed",
});

function normalizeStatus(value) {
  const raw = String(value || "").trim().toLowerCase();
  return STATUS_ALIAS[raw] || raw;
}

function normalizeCount(value) {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 0;
  }
  return Math.round(parsed);
}

function clampPercent(value) {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(parsed)));
}

function resolveAnalysisStatus({ caseInfo = null, currentTask = null } = {}) {
  if (currentTask?.status) {
    return normalizeStatus(currentTask.status);
  }
  return normalizeStatus(caseInfo?.analysis_status);
}

function resolveAnalysisMessage({ status = "", caseStage = null, currentTask = null } = {}) {
  if (currentTask?.message) {
    return String(currentTask.message).trim();
  }

  const stageDescription = String(caseStage?.description || "").trim();
  if (stageDescription) {
    return stageDescription;
  }

  switch (status) {
    case "pending_reanalysis":
      return "已收到补充材料，等待重新解析。";
    case "retrying":
      return "系统正在自动重试，请稍候。";
    case "pending":
      return "任务已入队，正在等待处理。";
    case "processing":
      return "任务处理中，请稍候。";
    case "failed":
      return "任务处理失败，请刷新后重试。";
    default:
      return "任务状态更新中。";
  }
}

function resolveStatusText(status) {
  switch (status) {
    case "pending_reanalysis":
      return "等待重新解析";
    case "retrying":
      return "自动重试中";
    case "pending":
      return "排队中";
    case "processing":
      return "处理中";
    case "failed":
      return "处理失败";
    default:
      return "状态更新中";
  }
}

export function buildCaseTopFeedbackBanner({
  caseInfo = null,
  caseStage = null,
  networkNoticeText = "",
  uploadSessionNotice = "",
  failedCount = 0,
  pendingQueueCount = 0,
  autoResumePending = false,
  canUploadFiles = true,
} = {}) {
  const normalizedNetworkNotice = String(networkNoticeText || "").trim();
  if (normalizedNetworkNotice) {
    return {
      tone: "warning",
      title: "网络状态提醒",
      message: normalizedNetworkNotice,
      actionLabel: "",
    };
  }

  const normalizedFailedCount = normalizeCount(failedCount);
  const normalizedPendingCount = normalizeCount(pendingQueueCount);
  if (normalizedFailedCount > 0) {
    const waitingText =
      normalizedPendingCount > 0
        ? `当前仍有 ${normalizedPendingCount} 份材料待处理。`
        : "失败材料会保留在队列中。";
    const retryHint = autoResumePending
      ? "网络恢复后会自动继续上传，也可以手动重试。"
      : "建议继续上传或逐个重试失败材料。";
    return {
      tone: "warning",
      title: `有 ${normalizedFailedCount} 份材料上传失败`,
      message: `${waitingText}${retryHint}`,
      actionLabel: canUploadFiles ? "继续上传" : "",
    };
  }

  const normalizedUploadNotice = String(uploadSessionNotice || "").trim();
  if (normalizedUploadNotice) {
    return {
      tone: "success",
      title: "上传状态更新",
      message: normalizedUploadNotice,
      actionLabel: "",
    };
  }

  const analysisStatus = resolveAnalysisStatus({ caseInfo });
  if (!analysisStatus) {
    return null;
  }

  if (analysisStatus === "failed") {
    return {
      tone: "danger",
      title: "智能任务处理异常",
      message: "请刷新页面确认最新状态，必要时可联系律师继续处理。",
      actionLabel: "刷新状态",
    };
  }

  if (analysisStatus === "completed") {
    return {
      tone: "success",
      title: "智能分析已完成",
      message: String(caseStage?.description || "你可以查看解析结果和最新报告。"),
      actionLabel: "",
    };
  }

  if (isCaseAnalysisInProgress(analysisStatus)) {
    return {
      tone: "info",
      title: "智能分析进行中",
      message: String(caseStage?.description || "任务进行中，可离开页面稍后查看。"),
      actionLabel: "",
    };
  }

  return null;
}

export function buildCaseLongTaskCard({ caseInfo = null, caseStage = null, currentTask = null, wsConnected = false } = {}) {
  const status = resolveAnalysisStatus({ caseInfo, currentTask });
  if (!status || status === "completed") {
    return null;
  }

  if (!isCaseAnalysisInProgress(status) && status !== "failed") {
    return null;
  }

  const progress = clampPercent(currentTask?.progress ?? caseInfo?.analysis_progress ?? 0);
  const failed = status === "failed";
  const tone = failed ? "danger" : status === "pending_reanalysis" || status === "retrying" ? "warning" : "info";

  return {
    tone,
    title: failed ? "智能任务处理异常" : "智能任务状态",
    statusText: resolveStatusText(status),
    progress,
    progressText: failed ? "处理中断" : `当前进度 ${progress}%`,
    message: resolveAnalysisMessage({
      status,
      caseStage,
      currentTask,
    }),
    hint: failed
      ? "建议刷新后重试，若仍失败请联系律师处理。"
      : wsConnected
        ? "实时通道已连接"
        : "实时通道重连中，已启用轮询兜底",
    actionLabel: failed ? "刷新状态" : "",
  };
}

export function buildUploadFailureFeedback({
  failedCount = 0,
  pendingQueueCount = 0,
  autoResumePending = false,
} = {}) {
  const normalizedFailedCount = normalizeCount(failedCount);
  if (normalizedFailedCount <= 0) {
    return null;
  }

  const normalizedPendingCount = Math.max(normalizedFailedCount, normalizeCount(pendingQueueCount));
  if (autoResumePending) {
    return {
      title: `有 ${normalizedFailedCount} 份材料上传中断`,
      message: `网络恢复后会自动继续上传，当前仍有 ${normalizedPendingCount} 份待处理。`,
      actionLabel: normalizedPendingCount > 1 ? `继续上传 ${normalizedPendingCount} 份` : "继续上传",
    };
  }

  return {
    title: `有 ${normalizedFailedCount} 份材料上传失败`,
    message: `失败材料已保留在队列中，当前待处理 ${normalizedPendingCount} 份，可继续上传或逐个重试。`,
    actionLabel: normalizedPendingCount > 1 ? `继续上传 ${normalizedPendingCount} 份` : "继续上传",
  };
}
