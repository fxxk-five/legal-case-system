import { friendlyError } from "../../shared/lib/form";
import { filesApi } from "../../shared/api/domain-api";

const MAX_UPLOAD_SIZE = 20 * 1024 * 1024;
const ALLOWED_UPLOAD_EXTENSIONS = new Set(["jpg", "jpeg", "png", "gif", "webp", "pdf", "doc", "docx", "xls", "xlsx"]);

const STATUS_TEXT_MAP = {
  waiting: "待上传",
  uploading: "上传中",
  success: "已上传",
  failed: "上传失败",
};

const STATUS_TAG_CLASS_MAP = {
  waiting: "tag-neutral",
  uploading: "tag-primary",
  success: "tag-success",
  failed: "tag-danger",
};

function createStateEmitter(initialState = {}) {
  let currentState = {
    selectedFiles: [],
    submitting: false,
    uploadSessionNotice: "",
    autoResumePending: false,
    ...(initialState || {}),
  };
  let onStateChange = null;

  return {
    setHandler(handler) {
      onStateChange = typeof handler === "function" ? handler : null;
    },
    patch(patch = {}) {
      currentState = {
        ...currentState,
        ...(patch || {}),
      };
      onStateChange?.(patch, currentState);
      return currentState;
    },
    get() {
      return currentState;
    },
  };
}

function buildFileItem(file, index, sourceText) {
  const rawName = file.name || file.path || `file-${index + 1}`;
  const name = String(rawName).split(/[\\/]/).pop();
  const size = Number(file?.size ?? file?.fileSize ?? 0) || 0;
  const extension = String(name).includes(".") ? String(name).split(".").pop().toLowerCase() : "";
  return {
    uid: `${Date.now()}-${index}-${Math.random().toString(16).slice(2)}`,
    name,
    path: file.path || file.tempFilePath || "",
    size,
    extension,
    sourceText,
    status: "waiting",
    statusText: STATUS_TEXT_MAP.waiting,
    statusTagClass: STATUS_TAG_CLASS_MAP.waiting,
    description: "",
    error: "",
    progress: 0,
    progressText: "等待上传",
    uploadedFileId: null,
    retryableNetworkFailure: false,
  };
}

function clampProgress(value, max = 100) {
  const number = Number(value || 0);
  if (Number.isNaN(number)) {
    return 0;
  }
  return Math.max(0, Math.min(max, Math.round(number)));
}

function buildDuplicateKey(name = "", size = 0) {
  const normalizedName = String(name || "").trim().toLowerCase();
  return `${normalizedName}::${size || "unknown"}`;
}

function collectDisplayNames(items = [], limit = 3) {
  const names = items
    .map((item) => String(item?.name || item?.file_name || "").trim())
    .filter(Boolean)
    .slice(0, limit);
  return names.join("、");
}

function buildInvalidFilesMessage({ oversizedItems = [], unsupportedItems = [], invalidPathItems = [] } = {}) {
  const notices = [];

  if (oversizedItems.length) {
    notices.push(
      `已跳过超过 20MB 的材料：${collectDisplayNames(oversizedItems)}${
        oversizedItems.length > 3 ? ` 等 ${oversizedItems.length} 份` : ""
      }。`,
    );
  }

  if (unsupportedItems.length) {
    notices.push(
      `已跳过暂不支持的格式：${collectDisplayNames(unsupportedItems)}${
        unsupportedItems.length > 3 ? ` 等 ${unsupportedItems.length} 份` : ""
      }。可先截图后以图片上传。`,
    );
  }

  if (invalidPathItems.length) {
    notices.push("有部分材料未能识别，请重新选择后再试。");
  }

  return notices.join("\n\n");
}

function buildDuplicateFilesMessage(items = []) {
  return `发现 ${items.length} 份材料可能已经在队列中或已上传：${collectDisplayNames(items)}${
    items.length > 3 ? ` 等 ${items.length} 份` : ""
  }。仍要加入队列吗？`;
}

function isProbablyNetworkError(error) {
  const text = `${error?.detail || ""} ${error?.errMsg || ""} ${error?.code || ""}`.toLowerCase();
  return (
    text.includes("network") ||
    text.includes("timeout") ||
    text.includes("request:fail") ||
    text.includes("uploadfile:fail") ||
    text.includes("连接") ||
    text.includes("网络") ||
    text.includes("断开") ||
    text.includes("socket")
  );
}

async function defaultUploadCaseFile({ caseId, filePath, description = "", onProgress } = {}) {
  return filesApi.uploadCaseFile({
    caseId,
    filePath,
    description,
    onProgress,
  });
}

export function createUploadSessionController(dependencies = {}) {
  const api = {
    uploadCaseFile: dependencies.uploadCaseFile || defaultUploadCaseFile,
  };

  const state = createStateEmitter();

  function setHandler(handler) {
    state.setHandler(handler);
  }

  function dispose() {
    state.setHandler(null);
  }

  function getState() {
    return state.get();
  }

  function getSelectedFiles() {
    return Array.isArray(state.get().selectedFiles) ? state.get().selectedFiles : [];
  }

  function findSelectedFileIndex(uid) {
    return getSelectedFiles().findIndex((item) => item.uid === uid);
  }

  function getSelectedFile(uid) {
    const index = findSelectedFileIndex(uid);
    return index === -1 ? null : getSelectedFiles()[index];
  }

  function patchSelectedFiles(nextFiles, extraPatch = {}) {
    return state.patch({
      selectedFiles: Array.isArray(nextFiles) ? nextFiles : [],
      ...(extraPatch || {}),
    });
  }

  function updateSelectedFile(uid, patch) {
    const currentFiles = getSelectedFiles();
    const index = findSelectedFileIndex(uid);
    if (index === -1) {
      return null;
    }

    const nextItem = {
      ...currentFiles[index],
      ...(patch || {}),
    };
    const nextFiles = [...currentFiles];
    nextFiles.splice(index, 1, nextItem);
    patchSelectedFiles(nextFiles);
    return nextItem;
  }

  function setFileStatus(uid, status, extra = {}) {
    return updateSelectedFile(uid, {
      status,
      statusText: STATUS_TEXT_MAP[status] || "处理中",
      statusTagClass: STATUS_TAG_CLASS_MAP[status] || "tag-neutral",
      ...(extra || {}),
    });
  }

  function syncAutoResumePending(extraPatch = {}) {
    const autoResumePending = getSelectedFiles().some(
      (item) => item.status === "failed" && item.retryableNetworkFailure,
    );
    state.patch({
      autoResumePending,
      ...(extraPatch || {}),
    });
    return autoResumePending;
  }

  function getPendingQueueCount() {
    return getSelectedFiles().filter((item) => ["waiting", "failed"].includes(item.status)).length;
  }

  function isAnyUploading() {
    const currentState = state.get();
    return Boolean(currentState.submitting) || getSelectedFiles().some((item) => item.status === "uploading");
  }

  function findDuplicateItems(items = [], uploadedFiles = []) {
    const queueKeys = new Set();
    const queueNames = new Set();

    getSelectedFiles().forEach((item) => {
      const normalizedName = String(item?.name || "").trim().toLowerCase();
      if (normalizedName) {
        queueNames.add(normalizedName);
      }
      queueKeys.add(buildDuplicateKey(item?.name, item?.size));
    });

    const uploadedKeys = new Set();
    const uploadedNames = new Set();
    (Array.isArray(uploadedFiles) ? uploadedFiles : []).forEach((item) => {
      const name = String(item?.original_filename || item?.file_name || item?.name || "").trim();
      if (!name) {
        return;
      }
      uploadedNames.add(name.toLowerCase());
      uploadedKeys.add(buildDuplicateKey(name, Number(item?.file_size ?? item?.size ?? 0) || 0));
    });

    const batchKeys = new Set();
    return (Array.isArray(items) ? items : []).filter((item) => {
      const normalizedName = String(item?.name || "").trim().toLowerCase();
      const duplicateKey = buildDuplicateKey(item?.name, item?.size);
      const duplicated =
        batchKeys.has(duplicateKey) ||
        queueKeys.has(duplicateKey) ||
        uploadedKeys.has(duplicateKey) ||
        (normalizedName && (queueNames.has(normalizedName) || uploadedNames.has(normalizedName)));

      batchKeys.add(duplicateKey);
      return duplicated;
    });
  }

  async function appendFiles({
    files,
    sourceText,
    uploadedFiles = [],
    onInvalidFiles,
    onConfirmDuplicates,
  } = {}) {
    if (!Array.isArray(files) || !files.length || isAnyUploading()) {
      return {
        appendedCount: 0,
      };
    }

    const builtItems = files.map((file, index) => buildFileItem(file, index, sourceText));
    const invalidPathItems = builtItems.filter((item) => !item.path);
    const oversizedItems = builtItems.filter((item) => item.path && item.size > MAX_UPLOAD_SIZE);
    const unsupportedItems = builtItems.filter(
      (item) => item.path && item.extension && !ALLOWED_UPLOAD_EXTENSIONS.has(item.extension),
    );
    let nextItems = builtItems.filter(
      (item) =>
        item.path &&
        item.size <= MAX_UPLOAD_SIZE &&
        (!item.extension || ALLOWED_UPLOAD_EXTENSIONS.has(item.extension)),
    );

    if ((invalidPathItems.length || oversizedItems.length || unsupportedItems.length) && typeof onInvalidFiles === "function") {
      await onInvalidFiles(
        buildInvalidFilesMessage({
          invalidPathItems,
          oversizedItems,
          unsupportedItems,
        }),
      );
    }

    if (!nextItems.length) {
      return {
        appendedCount: 0,
      };
    }

    const duplicateItems = findDuplicateItems(nextItems, uploadedFiles);
    if (duplicateItems.length) {
      let keepDuplicates = true;
      if (typeof onConfirmDuplicates === "function") {
        keepDuplicates = await onConfirmDuplicates(buildDuplicateFilesMessage(duplicateItems));
      }

      if (!keepDuplicates) {
        const duplicateIds = new Set(duplicateItems.map((item) => item.uid));
        nextItems = nextItems.filter((item) => !duplicateIds.has(item.uid));
      }
    }

    if (!nextItems.length) {
      return {
        appendedCount: 0,
      };
    }

    patchSelectedFiles([...getSelectedFiles(), ...nextItems], {
      uploadSessionNotice: "",
    });

    return {
      appendedCount: nextItems.length,
    };
  }

  function removeFile(index) {
    const currentFiles = getSelectedFiles();
    const target = currentFiles[index];
    if (!target || target.status === "uploading" || isAnyUploading()) {
      return false;
    }

    const nextFiles = [...currentFiles];
    nextFiles.splice(index, 1);
    patchSelectedFiles(nextFiles);
    syncAutoResumePending();
    return true;
  }

  async function uploadQueueItem({ uid, caseId, onFileUploaded } = {}) {
    const item = getSelectedFile(uid);
    if (!item) {
      return {
        success: false,
        networkFailure: false,
      };
    }

    if (!item.path) {
      setFileStatus(uid, "failed", {
        error: "文件路径无效",
        progress: 0,
        progressText: "上传失败",
        retryableNetworkFailure: false,
      });
      syncAutoResumePending();
      return {
        success: false,
        networkFailure: false,
      };
    }

    state.patch({
      uploadSessionNotice: "",
    });
    setFileStatus(uid, "uploading", {
      error: "",
      progress: 0,
      progressText: "准备上传...",
      retryableNetworkFailure: false,
    });

    try {
      const uploaded = await api.uploadCaseFile({
        caseId,
        filePath: item.path,
        description: item.description,
        onProgress: (event) => {
          const rawProgress = clampProgress(event?.progress, 100);
          const progress = rawProgress >= 100 ? 99 : Math.max(1, rawProgress);
          setFileStatus(uid, "uploading", {
            progress,
            progressText: `已上传 ${progress}%`,
          });
        },
      });

      setFileStatus(uid, "success", {
        error: "",
        progress: 100,
        progressText: "上传完成",
        uploadedFileId: uploaded?.id || null,
        retryableNetworkFailure: false,
      });
      syncAutoResumePending();

      if (typeof onFileUploaded === "function") {
        try {
          await onFileUploaded(uploaded);
        } catch {
          // Keep upload success even if optimistic UI callback fails.
        }
      }

      return {
        success: true,
        uploaded,
        networkFailure: false,
      };
    } catch (error) {
      const current = getSelectedFile(uid);
      const progress = clampProgress(current?.progress, 99);
      const retryableNetworkFailure = isProbablyNetworkError(error);

      setFileStatus(uid, "failed", {
        error: retryableNetworkFailure
          ? "网络中断，恢复后会自动继续上传，也可以手动重试。"
          : friendlyError(error, "上传失败"),
        progress,
        progressText: progress > 0 ? `上传中断于 ${progress}%` : "上传失败",
        retryableNetworkFailure,
      });

      const autoResumePending = syncAutoResumePending();
      return {
        success: false,
        networkFailure: retryableNetworkFailure,
        autoResumePending,
      };
    }
  }

  async function retrySingleFile({
    uid,
    caseId,
    networkOnline = true,
    onFileUploaded,
    onReloadCaseInfo,
  } = {}) {
    if (isAnyUploading()) {
      return {
        started: false,
      };
    }

    if (!networkOnline) {
      return {
        started: false,
        errorMessage: "当前网络不可用，请联网后再试",
        networkNoticeText: "当前网络不可用，请联网后再试；已选材料会保留在队列中。",
      };
    }

    const result = await uploadQueueItem({
      uid,
      caseId,
      onFileUploaded,
    });
    if (!result.success) {
      return {
        started: true,
        successCount: 0,
        remainingCount: getPendingQueueCount(),
        autoResumePending: Boolean(state.get().autoResumePending),
        networkNoticeText: result.networkFailure ? "网络恢复后会自动继续上传未完成材料。" : "",
      };
    }

    const nextFiles = getSelectedFiles().filter((item) => item.uid !== uid);
    patchSelectedFiles(nextFiles);
    const autoResumePending = syncAutoResumePending();
    state.patch({
      uploadSessionNotice: "律师已收到你刚刚补充的 1 份材料，正在继续整理。",
      autoResumePending,
    });

    if (typeof onReloadCaseInfo === "function") {
      try {
        await onReloadCaseInfo();
      } catch {
        // Keep local optimistic status when refresh fails.
      }
    }

    return {
      started: true,
      successCount: 1,
      remainingCount: getPendingQueueCount(),
      autoResumePending,
      successToastText: "材料已重新上传",
      networkNoticeText: autoResumePending ? "网络恢复后会自动继续上传未完成材料。" : "",
    };
  }

  async function continuePendingUploads({
    caseId,
    canUploadFiles = true,
    networkOnline = true,
    skipConfirm = false,
    silent = false,
    confirmUpload,
    onFileUploaded,
    onReloadCaseInfo,
  } = {}) {
    const pendingQueueCount = getPendingQueueCount();
    if (!canUploadFiles) {
      return {
        started: false,
        successCount: 0,
        remainingCount: pendingQueueCount,
        errorMessage: silent ? "" : "当前案件不允许继续上传材料",
      };
    }

    if (!pendingQueueCount || isAnyUploading()) {
      return {
        started: false,
        successCount: 0,
        remainingCount: pendingQueueCount,
      };
    }

    if (!networkOnline) {
      return {
        started: false,
        successCount: 0,
        remainingCount: pendingQueueCount,
        errorMessage: silent ? "" : "当前网络不可用，请联网后再上传",
        networkNoticeText: "当前网络不可用，请联网后再上传；已选材料会保留在队列中。",
      };
    }

    if (!skipConfirm && typeof confirmUpload === "function") {
      const confirmed = await confirmUpload();
      if (!confirmed) {
        return {
          started: false,
          successCount: 0,
          remainingCount: pendingQueueCount,
        };
      }
    }

    state.patch({
      submitting: true,
      uploadSessionNotice: "",
    });

    let successCount = 0;
    const queueSnapshot = getSelectedFiles()
      .filter((item) => ["waiting", "failed"].includes(item.status))
      .map((item) => item.uid);

    try {
      for (const uid of queueSnapshot) {
        const result = await uploadQueueItem({
          uid,
          caseId,
          onFileUploaded,
        });
        if (result.success) {
          successCount += 1;
          continue;
        }

        const current = getSelectedFile(uid);
        if (!networkOnline || current?.retryableNetworkFailure) {
          break;
        }
      }
    } finally {
      state.patch({
        submitting: false,
      });
    }

    const remainingCount = getPendingQueueCount();
    if (successCount <= 0) {
      const autoResumePending = syncAutoResumePending();
      return {
        started: true,
        successCount,
        remainingCount,
        autoResumePending,
        networkNoticeText: autoResumePending ? "网络恢复后会自动继续上传未完成材料。" : "",
        errorMessage: silent
          ? ""
          : autoResumePending
            ? "网络不稳定，恢复后会自动继续上传未完成材料"
            : "没有文件上传成功，请检查后重试",
      };
    }

    if (remainingCount > 0) {
      const nextFiles = getSelectedFiles().filter((item) => item.status !== "success");
      patchSelectedFiles(nextFiles);
      const autoResumePending = syncAutoResumePending();
      const uploadSessionNotice = autoResumePending
        ? `律师已收到 ${successCount} 份新材料，剩余 ${remainingCount} 份会在网络恢复后继续上传。`
        : `律师已收到 ${successCount} 份新材料，仍有 ${remainingCount} 份需要你继续处理。`;

      state.patch({
        uploadSessionNotice,
        autoResumePending,
      });

      if (typeof onReloadCaseInfo === "function") {
        try {
          await onReloadCaseInfo();
        } catch {
          // Keep local optimistic status when refresh fails.
        }
      }

      return {
        started: true,
        successCount,
        remainingCount,
        autoResumePending,
        uploadSessionNotice,
        networkNoticeText: autoResumePending ? "网络恢复后会自动继续上传未完成材料。" : "",
        errorMessage: silent
          ? ""
          : autoResumePending
            ? `已成功上传 ${successCount} 份材料，剩余材料会在网络恢复后自动继续`
            : `已成功上传 ${successCount} 份材料，仍有 ${remainingCount} 份需要处理后重试`,
      };
    }

    state.patch({
      selectedFiles: [],
      autoResumePending: false,
      uploadSessionNotice: `律师已收到你刚刚上传的 ${successCount} 份材料，正在继续整理。建议在案件补充说明里注明本批次主题。`,
    });

    if (typeof onReloadCaseInfo === "function") {
      try {
        await onReloadCaseInfo();
      } catch {
        // Keep local optimistic status when refresh fails.
      }
    }

    return {
      started: true,
      successCount,
      remainingCount: 0,
      autoResumePending: false,
      uploadSessionNotice: state.get().uploadSessionNotice,
      networkNoticeText: "",
      successToastText: `已上传 ${successCount} 份材料`,
    };
  }

  return {
    setHandler,
    dispose,
    getState,
    appendFiles,
    removeFile,
    retrySingleFile,
    continuePendingUploads,
  };
}
