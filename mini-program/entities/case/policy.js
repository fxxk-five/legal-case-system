const QUEUED_ANALYSIS_STATUSES = new Set(["queued", "pending", "retrying", "pending_reanalysis"]);
const FAILED_ANALYSIS_STATUSES = new Set(["failed", "dead"]);

export const caseStageMap = Object.freeze({
  awaiting_materials: Object.freeze({
    id: "awaiting_materials",
    label: "待上传材料",
    stepIndex: 0,
    tone: "neutral",
    primaryAction: Object.freeze({
      key: "upload_materials",
      label: "补充材料",
    }),
    locked: false,
    showAIResult: false,
    description: "请先把案件相关材料传给律师。",
    listHint: "待上传材料",
  }),
  uploading_materials: Object.freeze({
    id: "uploading_materials",
    label: "上传中",
    stepIndex: 0,
    tone: "primary",
    primaryAction: Object.freeze({
      key: "continue_upload",
      label: "继续上传",
    }),
    locked: true,
    showAIResult: false,
    description: "正在上传材料，请保持页面打开。",
    listHint: "上传进行中",
  }),
  upload_attention: Object.freeze({
    id: "upload_attention",
    label: "补传材料",
    stepIndex: 0,
    tone: "danger",
    primaryAction: Object.freeze({
      key: "retry_uploads",
      label: "重试上传",
    }),
    locked: false,
    showAIResult: false,
    description: "有材料上传失败，可在原位点重试。",
    listHint: "上传需处理",
  }),
  reviewing_materials: Object.freeze({
    id: "reviewing_materials",
    label: "律师整理中",
    stepIndex: 1,
    tone: "warning",
    primaryAction: Object.freeze({
      key: "view_progress",
      label: "查看进度",
    }),
    locked: true,
    showAIResult: false,
    description: "材料已收到，律师正在整理。",
    listHint: "处理中，请关注更新",
  }),
  analysis_completed: Object.freeze({
    id: "analysis_completed",
    label: "分析完成",
    stepIndex: 2,
    tone: "success",
    primaryAction: Object.freeze({
      key: "view_results",
      label: "查看结果",
    }),
    locked: false,
    showAIResult: true,
    description: "AI 结果和报告已可查看。",
    listHint: "分析结果可查看",
  }),
  attention_needed: Object.freeze({
    id: "attention_needed",
    label: "处理异常",
    stepIndex: 1,
    tone: "danger",
    primaryAction: Object.freeze({
      key: "upload_materials",
      label: "补充材料",
    }),
    locked: false,
    showAIResult: false,
    description: "处理遇到问题，可补充材料后继续推进。",
    listHint: "处理异常，需关注",
  }),
});

export const CASE_POLICY_CONTRACT_VERSION = "2026-03-25-v1";
export const CASE_STAGE_IDS = Object.freeze(Object.keys(caseStageMap));
export const CASE_CAPABILITY_FIELD_KEYS = Object.freeze([
  "canViewLawyerRemark",
  "canViewClientRemark",
  "canViewUploadGuide",
  "canViewInternalFileDescription",
  "canViewOwnFileDescription",
]);
export const CASE_CAPABILITY_ACTION_KEYS = Object.freeze([
  "canUploadFiles",
  "canDeleteAnyFile",
  "canDeleteOwnFile",
  "canDownloadAllFiles",
  "canDownloadOwnFiles",
  "canEditClientRemark",
  "canEditLawyerRemark",
  "canUpdateCaseStatus",
  "canEditUploadGuide",
  "canViewAIResults",
  "canAccessAITasks",
  "canDownloadLatestReport",
  "canGenerateInvite",
]);
export const CASE_FILE_CAPABILITY_FIELD_KEYS = Object.freeze(["canViewDescription"]);
export const CASE_FILE_CAPABILITY_ACTION_KEYS = Object.freeze(["canDownload", "canDelete"]);

export const CLIENT_CASE_STAGE_STEPS = Object.freeze([
  caseStageMap.awaiting_materials.label,
  caseStageMap.reviewing_materials.label,
  caseStageMap.analysis_completed.label,
]);

function normalizeStatus(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeRole(value) {
  const role = normalizeStatus(value);
  if (role === "org_lawyer" || role === "solo_lawyer") {
    return "lawyer";
  }
  return role;
}

function normalizeCount(value) {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 0;
  }
  return Math.round(parsed);
}

function createStage(id, overrides = {}) {
  const baseStage = caseStageMap[id] || caseStageMap.awaiting_materials;
  return {
    ...baseStage,
    primaryAction: { ...baseStage.primaryAction },
    ...overrides,
  };
}

function normalizeId(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isTenantAdminViewer(viewer) {
  return Boolean(viewer?.is_tenant_admin) || normalizeRole(viewer?.role) === "tenant_admin";
}

function isLawyerLikeViewer(viewer) {
  return ["tenant_admin", "lawyer"].includes(normalizeRole(viewer?.role));
}

function isClientViewer(viewer) {
  return normalizeRole(viewer?.role) === "client";
}

function isAssignedLawyer(viewer, caseItem) {
  return normalizeId(viewer?.id) > 0 && normalizeId(viewer?.id) === normalizeId(caseItem?.assigned_lawyer?.id);
}

function isClientOwner(viewer, caseItem) {
  return isClientViewer(viewer) && normalizeId(viewer?.id) > 0 && normalizeId(viewer?.id) === normalizeId(caseItem?.client?.id);
}

function resolveQueuedDescription(status) {
  switch (status) {
    case "pending_reanalysis":
      return {
        description: "已收到补充材料，等待重新解析。",
        listHint: "待重新解析",
      };
    case "retrying":
      return {
        description: "系统正在重试整理材料，请稍候。",
        listHint: "系统重试中",
      };
    default:
      return {
        description: "材料已收到，正在排队整理。",
        listHint: "材料已收到",
      };
  }
}

export function isCaseAnalysisInProgress(status) {
  const normalizedStatus = normalizeStatus(status);
  return normalizedStatus === "processing" || QUEUED_ANALYSIS_STATUSES.has(normalizedStatus);
}

export function resolveCaseStage(caseItem = {}, options = {}) {
  const caseStatus = normalizeStatus(caseItem?.status);
  const analysisStatus = normalizeStatus(caseItem?.analysis_status);
  const uploadingCount = normalizeCount(options.uploadingCount);
  const failedUploads = normalizeCount(options.failedUploads);
  const pendingUploads = normalizeCount(options.pendingUploads);
  const hasUploadedFiles =
    typeof options.hasUploadedFiles === "boolean"
      ? options.hasUploadedFiles
      : Array.isArray(caseItem?.files) && caseItem.files.length > 0;

  if (uploadingCount > 0) {
    return createStage("uploading_materials", {
      description: `正在上传 ${uploadingCount} 份材料，请保持页面打开。`,
      listHint: uploadingCount === 1 ? "1 份上传中" : `${uploadingCount} 份上传中`,
    });
  }

  if (failedUploads > 0) {
    return createStage("upload_attention", {
      description: `有 ${failedUploads} 份材料上传失败，可在原位点重试。`,
      listHint: failedUploads === 1 ? "1 份上传失败" : `${failedUploads} 份上传失败`,
    });
  }

  if (pendingUploads > 0) {
    return createStage("awaiting_materials", {
      description: `已选择 ${pendingUploads} 份材料，确认后即可上传给律师。`,
      listHint: pendingUploads === 1 ? "1 份待上传" : `${pendingUploads} 份待上传`,
    });
  }

  if (caseStatus === "done" || analysisStatus === "completed") {
    return createStage("analysis_completed", {
      locked: caseStatus === "done",
      description: caseStatus === "done" ? "案件已完成，AI 结果和报告可查看。" : "AI 结果和报告已可查看。",
      listHint: caseStatus === "done" ? "已完成" : "分析结果可查看",
    });
  }

  if (FAILED_ANALYSIS_STATUSES.has(analysisStatus)) {
    return createStage("attention_needed");
  }

  if (analysisStatus === "processing") {
    return createStage("reviewing_materials", {
      description: "律师正在整理你的材料，请耐心等待。",
      listHint: "正在整理中",
    });
  }

  if (QUEUED_ANALYSIS_STATUSES.has(analysisStatus)) {
    return createStage("reviewing_materials", resolveQueuedDescription(analysisStatus));
  }

  if (hasUploadedFiles || caseStatus === "processing") {
    return createStage("reviewing_materials");
  }

  return createStage("awaiting_materials");
}

export function buildCaseCapabilities({ viewer = null, caseItem = {}, stage = null } = {}) {
  const resolvedStage = stage?.id ? stage : resolveCaseStage(caseItem);
  const lawyerLike = isLawyerLikeViewer(viewer);
  const clientOwner = isClientOwner(viewer, caseItem);
  const caseEditor = lawyerLike && (isTenantAdminViewer(viewer) || isAssignedLawyer(viewer, caseItem));

  return {
    viewerRole: normalizeRole(viewer?.role),
    stageId: resolvedStage.id,
    fields: {
      canViewLawyerRemark: lawyerLike,
      canViewClientRemark: lawyerLike || clientOwner,
      canViewUploadGuide: lawyerLike || clientOwner,
      canViewInternalFileDescription: lawyerLike,
      canViewOwnFileDescription: clientOwner,
    },
    actions: {
      canUploadFiles: lawyerLike || clientOwner,
      canDeleteAnyFile: lawyerLike,
      canDeleteOwnFile: clientOwner,
      canDownloadAllFiles: lawyerLike,
      canDownloadOwnFiles: clientOwner,
      canEditClientRemark: clientOwner,
      canEditLawyerRemark: caseEditor,
      canUpdateCaseStatus: caseEditor,
      canEditUploadGuide: caseEditor,
      canViewAIResults: true,
      canAccessAITasks: lawyerLike,
      canDownloadLatestReport: lawyerLike || clientOwner,
      canGenerateInvite: lawyerLike,
    },
  };
}

export function buildCaseFileCapabilities({ viewer = null, caseItem = {}, fileItem = {}, caseCapabilities = null } = {}) {
  const resolvedCaseCapabilities = caseCapabilities || buildCaseCapabilities({ viewer, caseItem });
  const clientOwner = isClientOwner(viewer, caseItem);
  const ownClientFile =
    clientOwner &&
    normalizeRole(fileItem?.uploader_role) === "client" &&
    normalizeId(fileItem?.uploader_id) === normalizeId(viewer?.id);
  const canViewDescription =
    Boolean(fileItem?.description) &&
    (resolvedCaseCapabilities.fields.canViewInternalFileDescription || normalizeRole(fileItem?.uploader_role) !== "lawyer");

  return {
    fields: {
      canViewDescription,
    },
    actions: {
      canDownload: Boolean(fileItem?.can_download) && (resolvedCaseCapabilities.actions.canDownloadAllFiles || ownClientFile),
      canDelete: resolvedCaseCapabilities.actions.canDeleteAnyFile || ownClientFile,
    },
  };
}
