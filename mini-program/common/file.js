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

async function buildFileUrl(file) {
  const access = await get(`/files/${file.id}/access-link`);
  if (access.access_url.startsWith("http")) {
    return access.access_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${access.access_url}`;
}

async function downloadToTemp(file) {
  const url = await buildFileUrl(file);
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
