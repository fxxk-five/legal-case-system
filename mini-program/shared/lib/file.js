import { config } from "../../shared/config";
import { getAccessToken } from "../../features/auth/auth";
import { casesApi, filesApi } from "../api/domain-api";

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
  const access = await filesApi.getFileAccessLink(file.id);
  if (access.access_url.startsWith("http")) {
    return access.access_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${access.access_url}`;
}

async function buildLatestReportUrl(caseId) {
  const access = await casesApi.getLatestReportAccessLink(caseId);
  if (access.access_url.startsWith("http")) {
    return access.access_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${access.access_url}`;
}

async function buildReportVersionUrl(caseId, reportName) {
  const access = await casesApi.getReportVersionAccessLink(caseId, reportName);
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
