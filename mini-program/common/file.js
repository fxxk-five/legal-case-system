import { config } from "./config";
import { getAccessToken } from "./auth";

function buildHeaders() {
  const token = getAccessToken();
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

function buildFileUrl(file) {
  if (file.download_url?.startsWith("http")) {
    return file.download_url;
  }
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${file.download_url}`;
}

function downloadToTemp(file) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: buildFileUrl(file),
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
