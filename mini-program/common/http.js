import { config } from "./config";
import { clearSession, getAccessToken } from "./auth";

function request(url, options = {}) {
  const token = getAccessToken();
  const header = {
    "Content-Type": "application/json",
    ...(options.header || {}),
  };

  if (token) {
    header.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${config.apiBaseUrl}${url}`,
      method: options.method || "GET",
      data: options.data,
      header,
      success: ({ statusCode, data }) => {
        if (statusCode >= 200 && statusCode < 300) {
          resolve(data);
          return;
        }

        if (statusCode === 401) {
          clearSession();
          uni.reLaunch({ url: "/pages/login/index" });
        }

        reject(data);
      },
      fail: (error) => reject(error),
    });
  });
}

export function get(url) {
  return request(url);
}

export function post(url, data) {
  return request(url, { method: "POST", data });
}

export function patch(url, data) {
  return request(url, { method: "PATCH", data });
}

export function upload(url, filePath, name = "upload", formData = {}) {
  const token = getAccessToken();
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${config.apiBaseUrl}${url}`,
      filePath,
      name,
      formData,
      header: token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {},
      success: ({ statusCode, data }) => {
        let parsed = data;
        try {
          parsed = JSON.parse(data);
        } catch {
          parsed = { detail: data };
        }

        if (statusCode >= 200 && statusCode < 300) {
          resolve(parsed);
          return;
        }

        if (statusCode === 401) {
          clearSession();
          uni.reLaunch({ url: "/pages/login/index" });
        }
        reject(parsed);
      },
      fail: (error) => reject(error),
    });
  });
}
