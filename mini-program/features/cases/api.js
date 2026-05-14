import { casesApi, remarksApi } from "../../shared/api/domain-api";

export function getCaseDetail(caseId) {
  return casesApi.getCaseDetail(caseId);
}

export function updateClientRemark(caseId, remark) {
  return remarksApi.updateClientRemark(caseId, remark);
}

export function updateLawyerRemark(caseId, remark) {
  return remarksApi.updateLawyerRemark(caseId, remark);
}

export async function transcribeCaseRemarkAudio(filePath) {
  return remarksApi.transcribeCaseRemarkAudio(filePath);
}

export function getRemarkValue(payload, field, fallback = "") {
  return remarksApi.getRemarkValue(payload, field, fallback);
}

export function appendClientRemarkPreview(existingRemark, latestRemark) {
  return remarksApi.appendClientRemarkPreview(existingRemark, latestRemark);
}
