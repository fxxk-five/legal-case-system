import { config } from "./config";
import { getAccessToken } from "./auth";

const STATUS_ALIAS = {
  queued: "pending",
  running: "processing",
  success: "completed",
  error: "failed",
};

const TERMINAL_STATUS = new Set(["completed", "failed"]);

function normalizeTaskStatus(status) {
  if (!status) {
    return "pending";
  }
  return STATUS_ALIAS[status] || status;
}

export function normalizeTask(task = {}) {
  const progressValue = Number(task.progress ?? 0);
  return {
    ...task,
    task_id: task.task_id || task.id,
    status: normalizeTaskStatus(task.status),
    progress: Number.isNaN(progressValue) ? 0 : Math.max(0, Math.min(100, Math.round(progressValue))),
    message: task.message || task.error_message || "",
  };
}

export function getTaskStatusText(status) {
  const map = {
    pending: "排队中",
    queued: "排队中",
    processing: "执行中",
    running: "执行中",
    completed: "成功",
    success: "成功",
    failed: "失败",
    error: "失败",
  };
  return map[status] || "处理中";
}

function buildWsUrl(taskId, since = "") {
  const token = getAccessToken();
  const httpBase = config.apiBaseUrl || "http://127.0.0.1:8000/api/v1";
  const wsBase = httpBase.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:").replace(/\/api\/v1\/?$/i, "");

  const query = [];
  if (token) {
    query.push(`token=${encodeURIComponent(token)}`);
  }
  if (since) {
    query.push(`since=${encodeURIComponent(since)}`);
  }

  const suffix = query.length ? `?${query.join("&")}` : "";
  return `${wsBase}/ws/ai/tasks/${encodeURIComponent(taskId)}${suffix}`;
}

function inferStatusFromEvent(type, progress) {
  if (type === "completed") {
    return "completed";
  }
  if (type === "failed") {
    return "failed";
  }
  if (type === "progress") {
    return progress <= 0 ? "pending" : "processing";
  }
  return "processing";
}

export function createAITaskTracker(options = {}) {
  const pollIntervalMs = options.pollIntervalMs || 2000;
  const reconnectDelays = options.reconnectDelays || [1000, 2000, 5000];

  let currentTask = null;
  let pollTimer = null;
  let socketTask = null;
  let lastEventTimestamp = "";
  let connected = false;
  let stopped = true;
  let reconnectAttempts = 0;
  let reconnectTimer = null;

  function notifyUpdate(task, extra = {}) {
    if (typeof options.onUpdate === "function") {
      options.onUpdate(task, {
        connected,
        ...extra,
      });
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function closeSocket() {
    if (socketTask) {
      try {
        socketTask.close({ code: 1000, reason: "task tracker stopped" });
      } catch {
        // ignore socket close errors
      }
      socketTask = null;
    }
    connected = false;
  }

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function emitTerminal(task) {
    if (task.status === "completed" && typeof options.onCompleted === "function") {
      options.onCompleted(task);
    }
    if (task.status === "failed" && typeof options.onFailed === "function") {
      options.onFailed(task);
    }
  }

  function applyTaskPatch(patch = {}, extra = {}) {
    if (!currentTask) {
      return;
    }

    currentTask = normalizeTask({ ...currentTask, ...patch });
    notifyUpdate(currentTask, extra);

    if (TERMINAL_STATUS.has(currentTask.status)) {
      emitTerminal(currentTask);
      stop();
    }
  }

  async function pullTaskStatus(force = false) {
    if (!currentTask || !currentTask.task_id || typeof options.getTaskStatus !== "function") {
      return null;
    }

    if (!force && connected) {
      return null;
    }

    try {
      const latest = await options.getTaskStatus(currentTask.task_id);
      applyTaskPatch(latest, { source: "poll" });
      return latest;
    } catch (error) {
      if (typeof options.onError === "function") {
        options.onError(error);
      }
      return null;
    }
  }

  function handleSocketMessage(rawData) {
    let payload = rawData;
    if (typeof rawData === "string") {
      try {
        payload = JSON.parse(rawData);
      } catch {
        return;
      }
    }

    if (!payload || payload.task_id !== currentTask?.task_id) {
      return;
    }

    if (payload.timestamp) {
      lastEventTimestamp = payload.timestamp;
    }

    const progress = Number(payload.progress ?? 0);
    const status = inferStatusFromEvent(payload.type, Number.isNaN(progress) ? 0 : progress);

    applyTaskPatch(
      {
        status,
        progress,
        message: payload.message || payload.error || "",
        error_message: payload.error || null,
      },
      { source: "ws" }
    );
  }

  function scheduleReconnect() {
    if (stopped || !currentTask?.task_id) {
      return;
    }

    const index = Math.min(reconnectAttempts, reconnectDelays.length - 1);
    const delay = reconnectDelays[index];
    reconnectAttempts += 1;

    clearReconnectTimer();
    reconnectTimer = setTimeout(() => {
      openSocket();
      pullTaskStatus(true);
    }, delay);
  }

  function openSocket() {
    if (!currentTask?.task_id || stopped) {
      return;
    }

    closeSocket();

    const wsUrl = buildWsUrl(currentTask.task_id, lastEventTimestamp);
    socketTask = uni.connectSocket({ url: wsUrl });

    socketTask.onOpen(() => {
      connected = true;
      reconnectAttempts = 0;
      clearReconnectTimer();
      notifyUpdate(currentTask, { source: "ws-open" });
    });

    socketTask.onMessage((event) => {
      handleSocketMessage(event.data);
    });

    socketTask.onError(() => {
      connected = false;
      notifyUpdate(currentTask, { source: "ws-error" });
      pullTaskStatus(true);
      scheduleReconnect();
    });

    socketTask.onClose(() => {
      connected = false;
      notifyUpdate(currentTask, { source: "ws-close" });
      if (!stopped) {
        pullTaskStatus(true);
        scheduleReconnect();
      }
    });
  }

  function startPolling() {
    if (pollTimer || !currentTask?.task_id) {
      return;
    }

    pullTaskStatus(true);
    pollTimer = setInterval(() => {
      pullTaskStatus(false);
    }, pollIntervalMs);
  }

  function start(task) {
    if (!task) {
      return null;
    }

    stopped = false;
    reconnectAttempts = 0;
    lastEventTimestamp = "";
    currentTask = normalizeTask(task);

    notifyUpdate(currentTask, { source: "init" });

    if (TERMINAL_STATUS.has(currentTask.status)) {
      emitTerminal(currentTask);
      return currentTask;
    }

    startPolling();
    openSocket();
    return currentTask;
  }

  function stop() {
    stopped = true;
    stopPolling();
    clearReconnectTimer();
    closeSocket();
  }

  function replaceTask(task) {
    return start(task);
  }

  function getCurrentTask() {
    return currentTask;
  }

  return {
    start,
    stop,
    replaceTask,
    getCurrentTask,
    pullTaskStatus,
  };
}
