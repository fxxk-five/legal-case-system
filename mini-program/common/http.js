import { config } from "./config";
import { clearSession, getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from "./auth";
import { LOGIN_PAGE } from "./role-routing";

const STATUS_CODE_MAP = {
  400: "VALIDATION_ERROR",
  401: "AUTH_REQUIRED",
  403: "FORBIDDEN",
  404: "RESOURCE_NOT_FOUND",
  409: "CONFLICT",
  413: "PAYLOAD_TOO_LARGE",
  415: "UNSUPPORTED_MEDIA_TYPE",
  422: "VALIDATION_ERROR",
  500: "INTERNAL_ERROR",
  502: "EXTERNAL_SERVICE_ERROR",
  503: "EXTERNAL_SERVICE_ERROR",
  429: "CONFLICT",
  504: "EXTERNAL_SERVICE_ERROR",
};

const STATUS_MESSAGE_MAP = {
  413: "上传文件过大，请压缩后重试。",
  415: "文件格式不受支持，请更换文件后重试。",
  429: "请求过于频繁，请稍后再试。",
};

const STATUS_ALIAS = {
  queued: "pending",
  running: "processing",
  success: "completed",
  error: "failed",
};

const FILE_EXTENSION_MIME_MAP = {
  pdf: "application/pdf",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  txt: "text/plain",
};

function createRequestId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createIdempotencyKey(prefix = "ai-task") {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function resolveApiUrl(url = "") {
  if (String(url).startsWith("http")) {
    return url;
  }
  if (String(url).startsWith("/api/v1/")) {
    return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${url}`;
  }
  return `${config.apiBaseUrl}${url}`;
}

function inferContentType(fileName = "", rawType = "") {
  const normalizedType = String(rawType || "")
    .trim()
    .toLowerCase()
    .split(";", 1)[0];

  if (normalizedType.includes("/")) {
    return normalizedType;
  }

  const extension = String(fileName || "")
    .split(/[\\/]/)
    .pop()
    .split(".")
    .pop()
    .toLowerCase();

  if (normalizedType === "image") {
    return FILE_EXTENSION_MIME_MAP[extension] || "image/jpeg";
  }

  if (FILE_EXTENSION_MIME_MAP[extension]) {
    return FILE_EXTENSION_MIME_MAP[extension];
  }

  return "application/octet-stream";
}

function buildDefaultHeaders(extraHeaders = {}) {
  const token = getAccessToken();
  const header = {
    "Content-Type": "application/json",
    "X-Request-ID": createRequestId(),
    "X-Client-Platform": "mini-program",
    "X-Client-Source": "wx-mini",
    ...(extraHeaders || {}),
  };

  if (token) {
    header.Authorization = `Bearer ${token}`;
  }

  return header;
}

function normalizeTaskStatus(status) {
  if (!status) {
    return "pending";
  }
  return STATUS_ALIAS[status] || status;
}

function normalizeErrorPayload(payload, statusCode = 0) {
  const fallbackCode = STATUS_CODE_MAP[statusCode] || "INTERNAL_ERROR";

  if (!payload || typeof payload !== "object") {
    const fallbackMessage = statusCode
      ? STATUS_MESSAGE_MAP[statusCode] || "请求失败。"
      : "网络连接失败，请稍后重试。";
    return {
      code: fallbackCode,
      message: fallbackMessage,
      detail: fallbackMessage,
      status_code: statusCode,
    };
  }

  const message =
    (typeof payload.message === "string" && payload.message.trim()) ||
    (typeof payload.detail === "string" && payload.detail.trim()) ||
    STATUS_MESSAGE_MAP[statusCode] ||
    "请求失败。";

  return {
    ...payload,
    code: payload.code || fallbackCode,
    message,
    detail: payload.detail || message,
    status_code: statusCode,
  };
}

function handleUnauthorized() {
  clearSession();
  uni.reLaunch({ url: LOGIN_PAGE });
}

let refreshingPromise = null;

function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return Promise.resolve(false);
  }

  if (refreshingPromise) {
    return refreshingPromise;
  }

  refreshingPromise = new Promise((resolve) => {
    uni.request({
      url: resolveApiUrl("/auth/refresh"),
      method: "POST",
      data: { refresh_token: refreshToken },
      header: {
        "Content-Type": "application/json",
        "X-Request-ID": createRequestId(),
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
      },
      success: ({ statusCode, data }) => {
        if (statusCode >= 200 && statusCode < 300 && data && data.access_token) {
          setAccessToken(data.access_token);
          setRefreshToken(data.refresh_token || refreshToken);
          resolve(true);
          return;
        }
        resolve(false);
      },
      fail: () => resolve(false),
      complete: () => {
        refreshingPromise = null;
      },
    });
  });

  return refreshingPromise;
}

function request(url, options = {}) {
  const header = buildDefaultHeaders(options.header || {});
  const skipRefresh = Boolean(options._skipRefresh);

  return new Promise((resolve, reject) => {
    uni.request({
      url: resolveApiUrl(url),
      method: options.method || "GET",
      data: options.data,
      header,
      success: ({ statusCode, data }) => {
        if (statusCode >= 200 && statusCode < 300) {
          resolve(data);
          return;
        }

        if (statusCode === 401 && !skipRefresh) {
          refreshAccessToken()
            .then((refreshed) => {
              if (!refreshed) {
                handleUnauthorized();
                reject(normalizeErrorPayload(data, statusCode));
                return;
              }
              request(url, { ...options, _skipRefresh: true }).then(resolve).catch(reject);
            })
            .catch(() => {
              handleUnauthorized();
              reject(normalizeErrorPayload(data, statusCode));
            });
          return;
        }

        if (statusCode === 401) {
          handleUnauthorized();
        }

        reject(normalizeErrorPayload(data, statusCode));
      },
      fail: (error) => {
        reject(normalizeErrorPayload(error, 0));
      },
    });
  });
}

export function get(url, options = {}) {
  return request(url, { ...options, method: "GET" });
}

export function post(url, data, options = {}) {
  return request(url, { ...options, method: "POST", data });
}

export function put(url, data, options = {}) {
  return request(url, { ...options, method: "PUT", data });
}

export function patch(url, data, options = {}) {
  return request(url, { ...options, method: "PATCH", data });
}

export function del(url, options = {}) {
  return request(url, { ...options, method: "DELETE" });
}

export function sendSmsCode(data) {
  return post("/auth/sms/send", data);
}

export function verifySmsCode(data) {
  return post("/auth/sms/verify", data);
}

export function loginByPassword(data) {
  return post("/auth/login", data);
}

export function wxMiniLogin(data) {
  return post("/auth/wx-mini-login", data, { _skipRefresh: true });
}

export function wxMiniPhoneLogin(data) {
  return post("/auth/wx-mini-phone-login", data, { _skipRefresh: true });
}

export function wxMiniBindExisting(data) {
  return post("/auth/wx-mini-bind-existing", data, { _skipRefresh: true });
}

export async function refreshToken() {
  const ok = await refreshAccessToken();
  if (!ok) {
    throw normalizeErrorPayload({ code: "AUTH_REQUIRED", message: "登录状态已失效，请重新登录。" }, 401);
  }
  return {
    access_token: getAccessToken(),
    refresh_token: getRefreshToken(),
  };
}

export async function logoutByServer() {
  const refreshTokenValue = getRefreshToken();
  try {
    await post(
      "/auth/logout",
      { refresh_token: refreshTokenValue || null },
      {
        _skipRefresh: true,
      }
    );
  } catch {
    // Ignore logout API failures; local session cleanup still happens.
  } finally {
    clearSession();
  }
}

export function inviteRegister(data) {
  return post("/auth/invite-register", data);
}

export function upload(url, filePath, name = "upload", formData = {}, options = {}) {
  const header = buildDefaultHeaders(options.header || {});
  const skipRefresh = Boolean(options._skipRefresh);

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: resolveApiUrl(url),
      filePath,
      name,
      formData,
      header,
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

        if (statusCode === 401 && !skipRefresh) {
          refreshAccessToken()
            .then((refreshed) => {
              if (!refreshed) {
                handleUnauthorized();
                reject(normalizeErrorPayload(parsed, statusCode));
                return;
              }
              upload(url, filePath, name, formData, { ...options, _skipRefresh: true }).then(resolve).catch(reject);
            })
            .catch(() => {
              handleUnauthorized();
              reject(normalizeErrorPayload(parsed, statusCode));
            });
          return;
        }

        if (statusCode === 401) {
          handleUnauthorized();
        }

        reject(normalizeErrorPayload(parsed, statusCode));
      },
      fail: (error) => reject(normalizeErrorPayload(error, 0)),
    });
  });
}

export function uploadByPolicy(policy, filePath, options = {}) {
  const skipRefresh = Boolean(options._skipRefresh);
  const targetUrl = policy.upload_url.startsWith("http")
    ? policy.upload_url
    : `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${policy.upload_url}`;

  const isDirectPost = policy.mode === "direct_post";
  const mergedHeaders = isDirectPost
    ? {
        ...(policy.headers || {}),
        ...(options.header || {}),
      }
    : {
        "X-Request-ID": createRequestId(),
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
        ...(policy.headers || {}),
        ...(options.header || {}),
      };

  if (!isDirectPost) {
    const token = getAccessToken();
    if (token) {
      mergedHeaders.Authorization = `Bearer ${token}`;
    }
  }

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: targetUrl,
      filePath,
      name: policy.file_field_name || "upload",
      formData: policy.form_fields || {},
      header: mergedHeaders,
      success: ({ statusCode, data }) => {
        let parsed = data;
        try {
          parsed = JSON.parse(data);
        } catch {
          parsed = { detail: data };
        }

        if (statusCode >= 200 && statusCode < 300) {
          if (isDirectPost) {
            if (!policy.completion_url || !policy.completion_token) {
              reject(
                normalizeErrorPayload(
                  {
                    code: "FILE_UPLOAD_INVALID",
                    message: "Direct upload policy is missing completion metadata.",
                    detail: "Direct upload policy is missing completion metadata.",
                  },
                  400
                )
              );
              return;
            }

            post(
              policy.completion_url,
              {
                completion_token: policy.completion_token,
              },
              {
                _skipRefresh: skipRefresh,
              }
            )
              .then(resolve)
              .catch(reject);
            return;
          }
          resolve(parsed);
          return;
        }

        if (statusCode === 401 && !skipRefresh) {
          refreshAccessToken()
            .then((refreshed) => {
              if (!refreshed) {
                handleUnauthorized();
                reject(normalizeErrorPayload(parsed, statusCode));
                return;
              }
              uploadByPolicy(policy, filePath, { ...options, _skipRefresh: true }).then(resolve).catch(reject);
            })
            .catch(() => {
              handleUnauthorized();
              reject(normalizeErrorPayload(parsed, statusCode));
            });
          return;
        }

        if (statusCode === 401) {
          handleUnauthorized();
        }

        reject(normalizeErrorPayload(parsed, statusCode));
      },
      fail: (error) => reject(normalizeErrorPayload(error, 0)),
    });
  });
}

export function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!entries.length) {
    return "";
  }
  const query = entries
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join("&");
  return `?${query}`;
}

function normalizeTask(task = {}) {
  const progressValue = Number(task.progress ?? 0);
  return {
    ...task,
    task_id: task.task_id || task.id,
    status: normalizeTaskStatus(task.status),
    progress: Number.isNaN(progressValue) ? 0 : progressValue,
  };
}

function normalizeFact(item = {}) {
  const metadata = item.metadata || {};
  return {
    ...item,
    description: item.description || item.content || "",
    occurrence_time: item.occurrence_time || metadata.date || null,
    evidence_id: item.evidence_id !== undefined && item.evidence_id !== null ? item.evidence_id : (metadata.evidence_id !== undefined && metadata.evidence_id !== null ? metadata.evidence_id : null),
  };
}

function normalizeAnalysis(item = {}) {
  const resultData = item.result_data || {};
  return {
    ...item,
    summary: item.summary || resultData.summary || resultData.legal_opinion || "",
    win_rate: Number(item.win_rate !== undefined && item.win_rate !== null ? item.win_rate : (resultData.win_rate !== undefined && resultData.win_rate !== null ? resultData.win_rate : 0)),
  };
}

function normalizeFalsification(item = {}) {
  return {
    ...item,
    fact_description: item.fact_description || item.challenge_question || "",
    reason: item.reason || item.response || "",
    evidence_gap: item.evidence_gap || item.improvement_suggestion || null,
  };
}

function withIdempotencyHeaders(headers = {}, key) {
  return {
    ...headers,
    "Idempotency-Key": key || createIdempotencyKey(),
  };
}

async function ensureFileUploaded(caseId, fileOrId) {
  if (typeof fileOrId === "number") {
    return fileOrId;
  }

  if (typeof fileOrId === "string" && /^\d+$/.test(fileOrId)) {
    return Number(fileOrId);
  }

  if (!fileOrId || !fileOrId.path) {
    throw {
      code: "FILE_UPLOAD_INVALID",
      message: "缺少可解析的文件。",
      detail: "缺少可解析的文件。",
    };
  }

  const fileName = fileOrId.name || fileOrId.path || "upload-file";
  const contentType = inferContentType(fileName, fileOrId.type);
  const policyQuery = buildQuery({
    case_id: caseId,
    file_name: fileName,
    content_type: contentType,
  });
  const policy = await get(`/files/upload-policy${policyQuery}`);
  const uploaded = await uploadByPolicy(policy, fileOrId.path);

  if (!uploaded || !uploaded.id) {
    throw {
      code: "FILE_UPLOAD_INVALID",
      message: "文件上传成功但未返回文件ID。",
      detail: "文件上传成功但未返回文件ID。",
    };
  }

  return uploaded.id;
}

export async function getCaseFacts(caseId, params = {}) {
  const data = await get(`/ai/cases/${caseId}/facts${buildQuery(params)}`);
  return {
    ...data,
    items: (data.items || []).map(normalizeFact),
  };
}

export async function parseDocument(caseId, fileOrId, options = {}, idempotencyKey) {
  const fileId = await ensureFileUploaded(caseId, fileOrId);
  const data = await post(
    `/ai/cases/${caseId}/parse-document`,
    {
      file_id: fileId,
      parse_options: {
        extract_parties: true,
        extract_timeline: true,
        extract_evidence: true,
        extract_laws: true,
        ...options,
      },
    },
    {
      header: withIdempotencyHeaders({}, idempotencyKey),
    }
  );
  return normalizeTask(data);
}

export async function getAnalysisResults(caseId) {
  const data = await get(`/ai/cases/${caseId}/analysis-results`);
  return {
    ...data,
    items: (data.items || []).map(normalizeAnalysis),
  };
}

export async function startAnalysis(caseId, options = {}, idempotencyKey) {
  const data = await post(`/ai/cases/${caseId}/analyze`, options, {
    header: withIdempotencyHeaders({}, idempotencyKey),
  });
  return normalizeTask(data);
}

export async function getFalsificationResults(caseId) {
  const data = await get(`/ai/cases/${caseId}/falsification-results`);
  return {
    ...data,
    items: (data.items || []).map(normalizeFalsification),
  };
}

export async function startFalsification(caseId, analysisId, options = {}, idempotencyKey) {
  const data = await post(
    `/ai/cases/${caseId}/falsification`,
    {
      analysis_id: analysisId,
      ...options,
    },
    {
      header: withIdempotencyHeaders({}, idempotencyKey),
    }
  );
  return normalizeTask(data);
}

export async function getTaskStatus(taskId) {
  const data = await get(`/ai/tasks/${taskId}`);
  return normalizeTask(data);
}

export async function retryTask(taskId, reason = "") {
  const data = await post(`/ai/tasks/${taskId}/retry`, { reason: reason || null });
  return normalizeTask(data);
}
