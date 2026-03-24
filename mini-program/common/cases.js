import { get, patch, upload } from "./http";

function normalizeCaseId(caseId) {
  const parsed = Number(caseId);
  return Number.isNaN(parsed) ? caseId : parsed;
}

function normalizeRemarkText(value) {
  return String(value === null || value === undefined ? "" : value).trim();
}

export function getCaseDetail(caseId) {
  return get(`/cases/${normalizeCaseId(caseId)}`);
}

export function updateClientRemark(caseId, remark) {
  return patch(`/cases/${normalizeCaseId(caseId)}/client-remark`, {
    client_remark: normalizeRemarkText(remark),
  });
}

export function updateLawyerRemark(caseId, remark) {
  return patch(`/cases/${normalizeCaseId(caseId)}/lawyer-remark`, {
    lawyer_remark: normalizeRemarkText(remark),
  });
}

export async function transcribeCaseRemarkAudio(filePath) {
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
}

export function getRemarkValue(payload, field, fallback = "") {
  if (payload && typeof payload[field] === "string") {
    return payload[field];
  }
  return fallback;
}

export function appendClientRemarkPreview(existingRemark, latestRemark) {
  const previous = normalizeRemarkText(existingRemark);
  const next = normalizeRemarkText(latestRemark);
  if (!next) {
    return previous;
  }
  return previous ? `${previous}\n\n${next}` : next;
}
