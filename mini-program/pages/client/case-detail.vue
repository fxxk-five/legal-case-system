<template>
  <view class="page-container fade-in">
    <view class="card page-hero">
      <text class="page-hero-title">案件进度</text>
      <text class="page-hero-desc">
        你可以在这里查看案件概览、时间流、解析摘要、材料列表，并下载当前最新的 PDF 报告。
      </text>
      <view class="toolbar card-toolbar">
        <button v-if="canGoCaseList" class="toolbar-button toolbar-button-secondary action-button" @click="goCaseList">返回案件列表</button>
        <button class="toolbar-button toolbar-button-primary action-button" @click="loadPage">刷新详情</button>
      </view>
    </view>

    <view v-if="loading" class="card empty-state">正在加载案件数据...</view>

    <template v-else-if="caseInfo">
      <view class="card">
        <view class="row-between row-top">
          <view>
            <text class="section-title plain-title">案件概览</text>
            <text class="list-card-title">{{ caseInfo.title || '-' }}</text>
            <text class="list-card-subtitle">{{ caseInfo.case_number || '未生成案号' }}</text>
          </view>
          <text class="tag" :style="deadlineReminderStyle">{{ deadlineReminderText }}</text>
        </view>
        <text class="meta">法律类型：{{ legalTypeText }}</text>
        <text class="meta">负责律师：{{ lawyerName }}</text>
        <text class="meta">截止时间：{{ deadlineText }}</text>
        <text class="meta">创建时间：{{ createdAtText }}</text>
        <text class="meta">解析状态：{{ analysisStatusText }}</text>
      </view>

      <view class="card">
        <text class="section-title">案件操作</text>
        <text class="meta">当事人端仅提供最新 PDF 报告下载，不展示历史版本。</text>
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" :loading="reportDownloading" @click="downloadReport">下载最新报告</button>
          <button class="toolbar-button toolbar-button-secondary action-button" @click="goUploadMaterial">补充材料</button>
        </view>
      </view>

      <view class="card">
        <text class="section-title">时间流</text>
        <text class="meta">共 {{ timeline.length }} 条记录，仅展示对当事人可见的案件动态。</text>
        <view v-if="!timeline.length" class="empty-state">暂无可见时间流记录。</view>
        <view v-for="item in timeline" :key="item.timeline_key" class="timeline-item">
          <text class="timeline-time">{{ item.occurred_at_text }}</text>
          <text class="timeline-actor">{{ item.actor_text }}</text>
          <text class="timeline-desc">{{ item.description_text }}</text>
        </view>
      </view>

      <view class="card">
        <text class="section-title">智能解析结果</text>
        <template v-if="analysisCompleted && latestAnalysis">
          <text class="meta">事件摘要</text>
          <text class="summary-text">{{ latestAnalysis.summary || '暂无摘要' }}</text>
          <text class="meta">缺失证据提示</text>
          <view v-if="missingEvidenceHints.length">
            <text v-for="item in missingEvidenceHints" :key="item" class="warning-line">- {{ item }}</text>
          </view>
          <text v-else class="meta">暂无缺失证据提示。</text>
        </template>
        <template v-else>
          <text class="meta">当前进度：{{ analysisPercent }}%</text>
          <view class="progress-track">
            <view class="progress-fill progress-main" :style="progressStyle"></view>
          </view>
          <text class="meta">{{ progressMessage }}</text>
          <text class="meta">{{ wsStatusText }}</text>
        </template>
      </view>

      <view class="card">
        <text class="section-title">证据材料</text>
        <text class="meta">可查看与你权限匹配的材料；你本人上传的材料支持删除，律师侧内部材料按权限控制下载。</text>
        <view v-if="!files.length" class="empty-state">暂无材料，请先补充材料。</view>
        <view v-for="file in files" :key="file.id" class="file-item">
          <text class="list-card-title">{{ file.file_name }}</text>
          <text class="meta">解析状态：{{ file.parse_status_text }}</text>
          <text v-if="file.description" class="meta">说明：{{ file.description }}</text>
          <text class="meta">上传时间：{{ file.created_at_text }}</text>
          <view class="toolbar card-toolbar">
            <button class="toolbar-button toolbar-button-secondary action-button" :disabled="!file.can_download" @click="previewFile(file)">预览</button>
            <button class="toolbar-button toolbar-button-secondary action-button" :disabled="!file.can_download" @click="downloadFile(file)">下载</button>
            <button
              v-if="file.can_delete"
              class="toolbar-button toolbar-button-secondary action-button danger-action"
              :disabled="deletingFileId === file.id"
              @click="deleteOwnFile(file)"
            >
              删除
            </button>
          </view>
          <text v-if="!file.can_download" class="meta">该材料当前只展示名称，不支持下载。</text>
        </view>
      </view>
    </template>

    <view v-else class="card empty-state">
      当前没有可查看的案件。
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-secondary action-button" @click="goCaseList">返回案件列表</button>
      </view>
    </view>

    <client-tab-bar current-key="cases" />
  </view>
</template>

<script>
import ClientTabBar from "../../components/ClientTabBar.vue";
import { del, get, getAnalysisResults, getTaskStatus } from "../../common/http";
import { createAITaskTracker, normalizeTask } from "../../common/aiTask";
import { formatAnalysisStatus, formatDateTime, formatLegalType, getDeadlineReminder } from "../../common/display";
import { downloadCaseFile, openLatestCaseReport, previewCaseFile } from "../../common/file";
import { friendlyError, showFormError } from "../../common/form";
import { ensureClientAccess } from "../../common/session";

const IN_PROGRESS_STATUS = new Set(["queued", "pending", "processing", "retrying", "pending_reanalysis"]);
const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/gi;

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return fallback;
  }
  return parsed;
}

function parseStatusText(value) {
  const map = {
    pending: "待解析",
    processing: "解析中",
    completed: "已解析",
    failed: "解析失败",
  };
  return map[String(value || "").toLowerCase()] || value || "待解析";
}

export default {
  components: {
    ClientTabBar,
  },
  data() {
    return {
      loading: false,
      caseId: 0,
      totalCases: 0,
      caseInfo: null,
      timeline: [],
      files: [],
      latestAnalysis: null,
      currentTask: null,
      tracker: null,
      wsConnected: false,
      progressPollingTimer: null,
      reportDownloading: false,
      deletingFileId: 0,
    };
  },
  computed: {
    canGoCaseList() {
      return this.totalCases > 1;
    },
    legalTypeText() {
      return formatLegalType(this.caseInfo ? this.caseInfo.legal_type : "");
    },
    lawyerName() {
      return this.caseInfo && this.caseInfo.assigned_lawyer ? this.caseInfo.assigned_lawyer.real_name || "-" : "-";
    },
    createdAtText() {
      return formatDateTime(this.caseInfo ? this.caseInfo.created_at : "", "-");
    },
    deadlineText() {
      return formatDateTime(this.caseInfo ? this.caseInfo.deadline : "", "未设置");
    },
    deadlineReminderText() {
      return this.caseInfo ? getDeadlineReminder(this.caseInfo).text : "未设置";
    },
    deadlineReminderStyle() {
      return this.caseInfo ? getDeadlineReminder(this.caseInfo).style : "color:#475569;background:#e2e8f0;";
    },
    analysisCompleted() {
      return String(this.caseInfo?.analysis_status || "").toLowerCase() === "completed";
    },
    analysisPercent() {
      if (this.currentTask) {
        return Math.max(0, Math.min(100, toNumber(this.currentTask.progress, 0)));
      }
      return Math.max(0, Math.min(100, toNumber(this.caseInfo?.analysis_progress, 0)));
    },
    analysisStatusText() {
      return formatAnalysisStatus(this.caseInfo?.analysis_status, this.analysisPercent);
    },
    progressStyle() {
      return `width:${this.analysisPercent}%;`;
    },
    wsStatusText() {
      return this.wsConnected ? "实时通道已连接" : "实时通道重连中，轮询兜底已启用";
    },
    progressMessage() {
      if (this.currentTask?.message) {
        return this.currentTask.message;
      }
      const status = String(this.caseInfo?.analysis_status || "").toLowerCase();
      const map = {
        not_started: "等待触发解析",
        queued: "解析任务已入队，请稍候",
        pending: "解析任务已入队，请稍候",
        processing: "正在解析中，请稍候",
        retrying: "解析失败后正在自动重试",
        pending_reanalysis: "已收到补充材料，等待重新解析",
        completed: "解析已完成",
        failed: "解析失败，请稍后重试或联系律师",
        dead: "解析失败，请联系律师处理",
      };
      return map[status] || "处理中";
    },
    missingEvidenceHints() {
      if (!this.latestAnalysis) {
        return [];
      }
      const weaknesses = Array.isArray(this.latestAnalysis.weaknesses) ? this.latestAnalysis.weaknesses : [];
      const recommendations = Array.isArray(this.latestAnalysis.recommendations) ? this.latestAnalysis.recommendations : [];
      const merged = [...weaknesses, ...recommendations]
        .map((item) => String(item || "").trim())
        .filter(Boolean);
      return [...new Set(merged)].slice(0, 5);
    },
  },
  onLoad(options) {
    const caseId = Number(options.id || options.caseId || 0);
    this.caseId = Number.isNaN(caseId) ? 0 : caseId;
  },
  onShow() {
    if (!ensureClientAccess()) {
      return;
    }
    this.loadPage();
  },
  onUnload() {
    this.stopTracker();
    this.stopProgressPolling();
  },
  methods: {
    decorateTimeline(items) {
      return (Array.isArray(items) ? items : []).map((item, index) => ({
        ...item,
        timeline_key: `${item.occurred_at || "unknown"}-${index}`,
        occurred_at_text: formatDateTime(item.occurred_at, "-"),
        actor_text: this.formatTimelineActor(item),
        description_text: item.description || item.title || "-",
      }));
    },
    decorateFiles(items) {
      return (Array.isArray(items) ? items : []).map((item) => ({
        ...item,
        parse_status_text: parseStatusText(item.parse_status),
        created_at_text: formatDateTime(item.created_at, "-"),
        can_delete: item.uploader_role === "client",
      }));
    },
    formatTimelineActor(item) {
      const operatorName = String(item?.operator_name || "").trim();
      if (!operatorName) {
        return "系统";
      }
      const clientName = String(this.caseInfo?.client?.real_name || "").trim();
      if (clientName && operatorName === clientName) {
        return "您";
      }
      return operatorName;
    },
    extractLatestTaskId() {
      for (const item of this.timeline) {
        const text = `${item.description || ""} ${item.title || ""}`;
        const matches = String(text).match(UUID_PATTERN);
        if (matches && matches.length) {
          return matches[0];
        }
      }
      return "";
    },
    async loadPage() {
      this.loading = true;
      try {
        const cases = await get("/cases");
        const visibleCases = Array.isArray(cases) ? cases : [];
        this.totalCases = visibleCases.length;
        if (!visibleCases.length) {
          this.caseInfo = null;
          this.timeline = [];
          this.files = [];
          this.latestAnalysis = null;
          this.stopTracker();
          this.stopProgressPolling();
          return;
        }

        const targetCase = this.caseId
          ? visibleCases.find((item) => Number(item.id) === Number(this.caseId)) || visibleCases[0]
          : visibleCases[0];
        this.caseId = targetCase.id;

        const [caseDetail, fileList, analysisRes] = await Promise.all([
          get(`/cases/${this.caseId}`),
          get(`/cases/${this.caseId}/files`),
          getAnalysisResults(this.caseId),
        ]);

        this.caseInfo = caseDetail;
        this.timeline = this.decorateTimeline(caseDetail.timeline);
        this.files = this.decorateFiles(fileList);
        this.latestAnalysis = (analysisRes.items || [])[0] || null;
        this.syncProgressTracking();
      } catch (error) {
        showFormError(friendlyError(error, "加载案件详情失败"));
      } finally {
        this.loading = false;
      }
    },
    syncProgressTracking() {
      const status = String(this.caseInfo?.analysis_status || "").toLowerCase();
      if (!IN_PROGRESS_STATUS.has(status)) {
        this.stopTracker();
        this.stopProgressPolling();
        return;
      }

      this.startProgressPolling();
      const taskId = this.extractLatestTaskId();
      if (!taskId) {
        this.stopTracker();
        return;
      }
      if (this.currentTask?.task_id === taskId) {
        return;
      }
      this.startTracker(taskId);
    },
    startTracker(taskId) {
      this.stopTracker();
      this.currentTask = normalizeTask({
        task_id: taskId,
        status: this.caseInfo?.analysis_status || "pending",
        progress: this.caseInfo?.analysis_progress || 0,
        message: this.progressMessage,
      });

      this.tracker = createAITaskTracker({
        getTaskStatus,
        onUpdate: (nextTask, meta) => {
          this.currentTask = normalizeTask(nextTask);
          this.wsConnected = Boolean(meta && meta.connected);
        },
        onCompleted: async () => {
          this.wsConnected = false;
          await this.loadPage();
        },
        onFailed: async (failedTask) => {
          this.currentTask = normalizeTask(failedTask);
          this.wsConnected = false;
          await this.loadPage();
        },
      });

      this.tracker.start(this.currentTask);
    },
    stopTracker() {
      if (this.tracker) {
        this.tracker.stop();
        this.tracker = null;
      }
      this.currentTask = null;
      this.wsConnected = false;
    },
    startProgressPolling() {
      if (this.progressPollingTimer || !this.caseId) {
        return;
      }
      this.progressPollingTimer = setInterval(async () => {
        try {
          const detail = await get(`/cases/${this.caseId}`);
          this.caseInfo = detail;
          this.timeline = this.decorateTimeline(detail.timeline);
          if (!IN_PROGRESS_STATUS.has(String(detail.analysis_status || "").toLowerCase())) {
            this.stopProgressPolling();
            if (String(detail.analysis_status || "").toLowerCase() === "completed") {
              const analysisRes = await getAnalysisResults(this.caseId);
              this.latestAnalysis = (analysisRes.items || [])[0] || null;
            }
          }
        } catch {
          // Keep polling on transient errors.
        }
      }, 3000);
    },
    stopProgressPolling() {
      if (this.progressPollingTimer) {
        clearInterval(this.progressPollingTimer);
        this.progressPollingTimer = null;
      }
    },
    async previewFile(file) {
      if (!file.can_download) {
        showFormError("该文件当前不可下载或预览");
        return;
      }
      try {
        await previewCaseFile(file);
      } catch (error) {
        showFormError(friendlyError(error, "文件预览失败"));
      }
    },
    async downloadFile(file) {
      if (!file.can_download) {
        showFormError("该文件当前不可下载或预览");
        return;
      }
      try {
        await downloadCaseFile(file);
      } catch (error) {
        showFormError(friendlyError(error, "文件下载失败"));
      }
    },
    async deleteOwnFile(file) {
      if (!file.can_delete || this.deletingFileId) {
        return;
      }
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "确认删除",
          content: "删除后将无法恢复，是否继续？",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
      if (!confirmed) {
        return;
      }

      this.deletingFileId = file.id;
      try {
        await del(`/files/${file.id}`);
        uni.showToast({ title: "已删除", icon: "success" });
        await this.loadPage();
      } catch (error) {
        showFormError(friendlyError(error, "删除文件失败"));
      } finally {
        this.deletingFileId = 0;
      }
    },
    async downloadReport() {
      if (!this.caseInfo || this.reportDownloading) {
        return;
      }
      this.reportDownloading = true;
      try {
        await openLatestCaseReport(this.caseInfo.id);
      } catch (error) {
        showFormError(friendlyError(error, "报告下载失败"));
      } finally {
        this.reportDownloading = false;
      }
    },
    goUploadMaterial() {
      if (!this.caseInfo) {
        showFormError("当前没有可补充材料的案件");
        return;
      }
      uni.navigateTo({ url: `/pages/client/upload-material?caseId=${this.caseInfo.id}` });
    },
    goCaseList() {
      uni.redirectTo({ url: "/pages/client/case-list" });
    },
  },
};
</script>

<style scoped>
.card-toolbar {
  margin-top: 18rpx;
}

.action-button {
  width: 100%;
}

.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.row-top {
  align-items: flex-start;
}

.plain-title::before {
  display: none;
}

.timeline-item,
.file-item {
  padding: 24rpx 0;
  border-top: 1rpx solid #e2e8f0;
}

.timeline-item:first-of-type,
.file-item:first-of-type {
  border-top: 0;
  padding-top: 8rpx;
}

.timeline-time {
  display: block;
  color: #0f766e;
  font-size: 24rpx;
}

.timeline-actor {
  display: block;
  margin-top: 8rpx;
  color: #334155;
  font-size: 24rpx;
}

.timeline-desc {
  display: block;
  margin-top: 8rpx;
  color: #0f172a;
  line-height: 1.7;
}

.summary-text {
  display: block;
  margin-top: 12rpx;
  margin-bottom: 12rpx;
  line-height: 1.8;
  color: #0f172a;
}

.warning-line {
  display: block;
  margin-top: 8rpx;
  color: #b91c1c;
}

.progress-track {
  margin-top: 12rpx;
  height: 10rpx;
  border-radius: 999rpx;
  background: #e2e8f0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
}

.progress-main {
  background: linear-gradient(90deg, #0ea5e9, #14b8a6);
}

.danger-action {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fff1f2;
}
</style>
