import { createAITaskTracker, normalizeTask } from "../ai/aiTask";
import { aiTasksApi, casesApi, filesApi } from "../../shared/api/domain-api";
import { collectMissingEvidenceHints, mapCaseFileItems, mapCaseTimelineItems } from "../../entities/case/mapper";
import { buildCaseCapabilities, isCaseAnalysisInProgress, resolveCaseStage } from "../../entities/case/policy";

const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/gi;

function createStateEmitter() {
  let currentState = {};
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
    replace(nextState = {}) {
      currentState = {
        ...currentState,
        ...(nextState || {}),
      };
      onStateChange?.(nextState, currentState);
      return currentState;
    },
    get() {
      return currentState;
    },
  };
}

function resolveClientTimelineActor(caseInfo, item) {
  const operatorName = String(item?.operator_name || "").trim();
  if (!operatorName) {
    return "系统";
  }

  const clientName = String(caseInfo?.client?.real_name || "").trim();
  if (clientName && operatorName === clientName) {
    return "您";
  }

  return operatorName;
}

function extractLatestTaskId(items = []) {
  for (const item of Array.isArray(items) ? items : []) {
    const text = `${item?.description || ""} ${item?.title || ""}`;
    const matches = String(text).match(UUID_PATTERN);
    if (matches && matches.length) {
      return matches[0];
    }
  }
  return "";
}

function buildClientSnapshot({
  caseId = 0,
  totalCases = 0,
  caseInfo = null,
  rawFiles = [],
  latestAnalysis = null,
  viewer = null,
  currentTask = null,
  wsConnected = false,
} = {}) {
  const caseStage = resolveCaseStage(caseInfo, {
    hasUploadedFiles: Array.isArray(rawFiles) && rawFiles.length > 0,
  });
  const caseCapabilities = buildCaseCapabilities({
    viewer,
    caseItem: caseInfo,
    stage: caseStage,
  });

  return {
    caseId,
    totalCases,
    caseInfo,
    caseStage,
    caseCapabilities,
    timeline: mapCaseTimelineItems(caseInfo?.timeline, {
      actorResolver: (item) => resolveClientTimelineActor(caseInfo, item),
    }),
    files: mapCaseFileItems(rawFiles, {
      viewer,
      caseItem: caseInfo,
      caseCapabilities,
    }),
    latestAnalysis,
    missingEvidenceHints: collectMissingEvidenceHints(latestAnalysis),
    currentTask,
    wsConnected,
  };
}

function buildLawyerSnapshot({ caseId = 0, caseInfo = null, rawFiles = [], viewer = null } = {}) {
  const caseStage = resolveCaseStage(caseInfo, {
    hasUploadedFiles: Array.isArray(rawFiles) && rawFiles.length > 0,
  });
  const caseCapabilities = buildCaseCapabilities({
    viewer,
    caseItem: caseInfo,
    stage: caseStage,
  });

  return {
    caseId,
    caseInfo,
    caseStage,
    caseCapabilities,
    timeline: Array.isArray(caseInfo?.timeline) ? caseInfo.timeline : [],
    files: mapCaseFileItems(rawFiles, {
      viewer,
      caseItem: caseInfo,
      caseCapabilities,
    }),
  };
}

export function createClientCaseDetailController(dependencies = {}) {
  const api = {
    getCases: dependencies.getCases || (() => casesApi.listCases()),
    getCaseDetail: dependencies.getCaseDetail || ((caseId) => casesApi.getCaseDetail(caseId)),
    getCaseFiles: dependencies.getCaseFiles || ((caseId) => filesApi.listCaseFiles(caseId)),
    getAnalysisResults: dependencies.getAnalysisResults || ((caseId) => aiTasksApi.getCaseAnalysisResults(caseId)),
    getTaskStatus: dependencies.getTaskStatus || ((taskId) => aiTasksApi.getTaskStatus(taskId)),
  };
  const createTracker = dependencies.createTracker || createAITaskTracker;

  const state = createStateEmitter();
  let viewer = null;
  let rawCaseInfo = null;
  let rawFiles = [];
  let latestAnalysis = null;
  let tracker = null;
  let progressPollingTimer = null;

  function stopTracker() {
    if (tracker) {
      tracker.stop();
      tracker = null;
    }
    state.patch({
      currentTask: null,
      wsConnected: false,
    });
  }

  function stopProgressPolling() {
    if (progressPollingTimer) {
      clearInterval(progressPollingTimer);
      progressPollingTimer = null;
    }
  }

  function dispose() {
    stopTracker();
    stopProgressPolling();
    state.setHandler(null);
  }

  async function buildSnapshot(preferredCaseId = 0) {
    const cases = await api.getCases();
    const visibleCases = Array.isArray(cases) ? cases : [];

    if (!visibleCases.length) {
      rawCaseInfo = null;
      rawFiles = [];
      latestAnalysis = null;
      return buildClientSnapshot({
        caseId: 0,
        totalCases: 0,
        caseInfo: null,
        rawFiles: [],
        latestAnalysis: null,
        viewer,
      });
    }

    const targetCase = preferredCaseId
      ? visibleCases.find((item) => Number(item.id) === Number(preferredCaseId)) || visibleCases[0]
      : visibleCases[0];

    const [caseInfo, fileList, analysisRes] = await Promise.all([
      api.getCaseDetail(targetCase.id),
      api.getCaseFiles(targetCase.id),
      api.getAnalysisResults(targetCase.id),
    ]);

    rawCaseInfo = caseInfo || null;
    rawFiles = Array.isArray(fileList) ? fileList : [];
    latestAnalysis = (analysisRes?.items || [])[0] || null;

    return buildClientSnapshot({
      caseId: Number(targetCase.id) || 0,
      totalCases: visibleCases.length,
      caseInfo: rawCaseInfo,
      rawFiles,
      latestAnalysis,
      viewer,
    });
  }

  async function load({ preferredCaseId = 0, viewer: currentViewer = null, onStateChange } = {}) {
    viewer = currentViewer;
    if (typeof onStateChange === "function") {
      state.setHandler(onStateChange);
    }
    state.patch({ loading: true });

    try {
      const snapshot = await buildSnapshot(preferredCaseId);
      state.replace({
        ...snapshot,
        loading: false,
      });
      syncProgressTracking();
      return state.get();
    } catch (error) {
      state.patch({ loading: false });
      throw error;
    }
  }

  async function refreshAfterProgress() {
    const currentState = state.get() || {};
    if (!currentState.caseId) {
      return null;
    }

    const detail = await api.getCaseDetail(currentState.caseId);
    rawCaseInfo = detail || rawCaseInfo;

    if (!isCaseAnalysisInProgress(rawCaseInfo?.analysis_status)) {
      latestAnalysis = String(rawCaseInfo?.analysis_status || "").toLowerCase() === "completed"
        ? ((await api.getAnalysisResults(currentState.caseId))?.items || [])[0] || null
        : latestAnalysis;
    }

    const snapshot = buildClientSnapshot({
      caseId: currentState.caseId,
      totalCases: currentState.totalCases || 0,
      caseInfo: rawCaseInfo,
      rawFiles,
      latestAnalysis,
      viewer,
      currentTask: currentState.currentTask,
      wsConnected: currentState.wsConnected,
    });

    state.replace(snapshot);
    syncProgressTracking();

    return state.get();
  }

  function startProgressPolling() {
    const currentState = state.get() || {};
    if (progressPollingTimer || !currentState.caseId) {
      return;
    }

    progressPollingTimer = setInterval(async () => {
      try {
        await refreshAfterProgress();
      } catch {
        // Keep polling on transient errors.
      }
    }, 3000);
  }

  function startTracker(taskId) {
    stopTracker();

    const currentTask = normalizeTask({
      task_id: taskId,
      status: rawCaseInfo?.analysis_status || "pending",
      progress: rawCaseInfo?.analysis_progress || 0,
      message: state.get()?.caseStage?.description || "",
    });

    state.patch({
      currentTask,
      wsConnected: false,
    });

    tracker = createTracker({
      getTaskStatus: api.getTaskStatus,
      onUpdate: (nextTask, meta) => {
        state.patch({
          currentTask: normalizeTask(nextTask),
          wsConnected: Boolean(meta && meta.connected),
        });
      },
      onCompleted: async () => {
        state.patch({ wsConnected: false });
        await load({
          preferredCaseId: state.get()?.caseId || 0,
          viewer,
        });
      },
      onFailed: async (failedTask) => {
        state.patch({
          currentTask: normalizeTask(failedTask),
          wsConnected: false,
        });
        await load({
          preferredCaseId: state.get()?.caseId || 0,
          viewer,
        });
      },
    });

    tracker.start(currentTask);
  }

  function syncProgressTracking() {
    if (!isCaseAnalysisInProgress(rawCaseInfo?.analysis_status)) {
      stopTracker();
      stopProgressPolling();
      return;
    }

    startProgressPolling();
    const taskId = extractLatestTaskId(rawCaseInfo?.timeline);
    if (!taskId) {
      stopTracker();
      return;
    }

    if (state.get()?.currentTask?.task_id === taskId) {
      return;
    }

    startTracker(taskId);
  }

  return {
    load,
    dispose,
  };
}

export function createLawyerCaseDetailController(dependencies = {}) {
  const api = {
    getCaseDetail: dependencies.getCaseDetail || ((caseId) => casesApi.getCaseDetail(caseId)),
    getCaseFiles: dependencies.getCaseFiles || ((caseId) => filesApi.listCaseFiles(caseId)),
  };

  async function load({ caseId, viewer } = {}) {
    const [caseInfo, rawFiles] = await Promise.all([
      api.getCaseDetail(caseId),
      api.getCaseFiles(caseId),
    ]);

    return buildLawyerSnapshot({
      caseId: Number(caseId) || 0,
      caseInfo: caseInfo || null,
      rawFiles,
      viewer,
    });
  }

  return {
    load,
    dispose() {},
  };
}
