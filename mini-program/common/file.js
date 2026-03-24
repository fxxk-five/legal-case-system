import { config } from "./config";
import { getAccessToken } from "./auth";
import { get } from "./http";

function buildHeaders() {
  const token = getAccessToken();
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

function buildApiUrl(path) {
  if (String(path || "").startsWith("http")) {
    return path;
  }
  return `${config.apiBaseUrl}${path}`;
}

async function buildFileUrl(file) {
  const access = await get(`/files/${file.id}/access-link`);
  if (access.access_url.startsWith("http")) {
    return access.access_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${access.access_url}`;
}

async function buildLatestReportUrl(caseId) {
  const access = await get(`/cases/${caseId}/report/access-link`);
  if (access.access_url.startsWith("http")) {
    return access.access_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${access.access_url}`;
}

async function buildReportVersionUrl(caseId, reportName) {
  const safeReportName = encodeURIComponent(reportName);
  const access = await get(`/cases/${caseId}/reports/${safeReportName}/access-link`);
  if (access.access_url.startsWith("http")) {
    return access.access_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${access.access_url}`;
}

function downloadUrlToTemp(url) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url,
      header: buildHeaders(),
      success: (result) => {
        if (result.statusCode >= 200 && result.statusCode < 300) {
          resolve(result.tempFilePath);
          return;
        }
        reject({ detail: "下载文件失败" });
      },
      fail: (error) => reject(error),
    });
  });
}

async function downloadToTemp(file) {
  const url = await buildFileUrl(file);
  return downloadUrlToTemp(url);
}

export async function previewCaseFile(file) {
  const tempFilePath = await downloadToTemp(file);
  return new Promise((resolve, reject) => {
    uni.openDocument({
      filePath: tempFilePath,
      showMenu: true,
      success: resolve,
      fail: reject,
    });
  });
}

export async function downloadCaseFile(file) {
  const tempFilePath = await downloadToTemp(file);
  return new Promise((resolve, reject) => {
    uni.saveFile({
      tempFilePath,
      success: () => {
        uni.showToast({ title: "文件已保存", icon: "success" });
        resolve(true);
      },
      fail: reject,
    });
  });
}

export async function openLatestCaseReport(caseId) {
  const reportUrl = await buildLatestReportUrl(caseId);
  const tempFilePath = await downloadUrlToTemp(reportUrl);
  return new Promise((resolve, reject) => {
    uni.openDocument({
      filePath: tempFilePath,
      showMenu: true,
      success: resolve,
      fail: reject,
    });
  });
}

export async function openCaseReportVersion(caseId, reportName) {
  const reportUrl = await buildReportVersionUrl(caseId, reportName);
  const tempFilePath = await downloadUrlToTemp(reportUrl);
  return new Promise((resolve, reject) => {
    uni.openDocument({
      filePath: tempFilePath,
      showMenu: true,
      success: resolve,
      fail: reject,
    });
  });
}
