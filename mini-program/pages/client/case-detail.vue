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

    <view v-if="topFeedbackBanner" class="feedback-banner-wrap">
      <page-status-banner
        :tone="topFeedbackBanner.tone"
        :title="topFeedbackBanner.title"
        :message="topFeedbackBanner.message"
        :action-label="topFeedbackBanner.actionLabel"
        @action="handleTopFeedbackAction"
      />
    </view>

    <view v-if="loading" class="card empty-state">正在加载案件数据...</view>

    <template v-else-if="caseInfo">
      <!-- 案件进度步骤条 -->
      <view class="progress-bar-card">
        <view class="progress-steps">
          <view
            v-for="(step, idx) in progressSteps"
            :key="step.key"
            class="progress-step"
            :class="{ 'step-done': idx < caseStage.stepIndex, 'step-active': idx === caseStage.stepIndex, 'step-pending': idx > caseStage.stepIndex }"
          >
            <view class="step-dot">
              <text class="step-dot-text">{{ idx < caseStage.stepIndex ? '✓' : idx + 1 }}</text>
            </view>
            <text class="step-label">{{ step.label }}</text>
          </view>
          <view class="progress-line-wrap">
            <view class="progress-line" />
            <view class="progress-line-fill" :style="progressLineFillStyle" />
          </view>
        </view>
      </view>

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
        <view class="stage-desc-row">
          <text class="stage-desc-label">当前进度</text>
          <view class="stage-desc-badge" :class="stageBadgeClass">
            <text class="stage-desc-badge-text">{{ stageFriendlyLabel }}</text>
          </view>
          <text class="stage-desc-hint">{{ stageFriendlyHint }}</text>
        </view>
      </view>

      <view class="card">
        <text class="section-title">案件操作</text>
        <text class="meta">当事人端仅提供最新 PDF 报告下载，不展示历史版本。</text>
        <text class="meta">当前主动作：{{ caseStage.primaryAction.label }}</text>
        <view class="toolbar card-toolbar">
          <button
            v-if="caseCapabilities.actions.canDownloadLatestReport"
            class="toolbar-button toolbar-button-primary action-button"
            :loading="reportDownloading"
            @click="downloadReport"
          >
            下载最新报告
          </button>
          <button
            v-if="caseCapabilities.actions.canUploadFiles"
            class="toolbar-button toolbar-button-secondary action-button"
            @click="goUploadMaterial"
          >
            补充材料
          </button>
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
        <template v-else-if="analysisCompleted">
          <text class="meta">{{ caseStage.description }}</text>
        </template>
        <template v-else>
          <long-task-status-card
            v-if="analysisTaskCard"
            :tone="analysisTaskCard.tone"
            :title="analysisTaskCard.title"
            :status-text="analysisTaskCard.statusText"
            :progress="analysisTaskCard.progress"
            :progress-text="analysisTaskCard.progressText"
            :message="analysisTaskCard.message"
            :hint="analysisTaskCard.hint"
            :action-label="analysisTaskCard.actionLabel"
            @action="loadPage"
          />
          <text v-else class="meta">{{ caseStage.description }}</text>
        </template>
      </view>

      <view class="card">
        <text class="section-title">证据材料</text>
        <text class="meta">可查看与你权限匹配的材料；你本人上传的材料支持删除，律师侧内部材料按权限控制下载。</text>
        <view v-if="!files.length" class="empty-state">暂无材料，请先补充材料。</view>
        <view v-for="file in files" :key="file.id" class="file-item">
          <text class="list-card-title">{{ file.file_name }}</text>
          <text class="meta">解析状态：{{ file.parse_status_text }}</text>
          <text v-if="file.capabilities.fields.canViewDescription" class="meta">说明：{{ file.description }}</text>
          <text class="meta">上传时间：{{ file.created_at_text }}</text>
          <view class="toolbar card-toolbar">
            <button
              class="toolbar-button toolbar-button-secondary action-button"
              :disabled="!file.capabilities.actions.canDownload"
              @click="previewFile(file)"
            >
              预览
            </button>
            <button
              class="toolbar-button toolbar-button-secondary action-button"
              :disabled="!file.capabilities.actions.canDownload"
              @click="downloadFile(file)"
            >
              下载
            </button>
            <button
              v-if="file.capabilities.actions.canDelete"
              class="toolbar-button toolbar-button-secondary action-button danger-action"
              :disabled="deletingFileId === file.id"
              @click="deleteOwnFile(file)"
            >
              删除
            </button>
          </view>
          <text v-if="!file.capabilities.actions.canDownload" class="meta">该材料当前只展示名称，不支持下载。</text>
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
import LongTaskStatusCard from "../../components/LongTaskStatusCard.vue";
import PageStatusBanner from "../../components/PageStatusBanner.vue";
import { createClientCaseDetailController } from "../../features/cases/detail-controller";
import { buildCaseLongTaskCard, buildCaseTopFeedbackBanner } from "../../features/cases/feedback";
import { filesApi } from "../../shared/api/domain-api";
import { formatAnalysisStatus, formatDateTime, formatLegalType, getDeadlineReminder } from "../../shared/lib/display";
import { downloadCaseFile, openLatestCaseReport, previewCaseFile } from "../../shared/lib/file";
import { friendlyError, showFormError } from "../../shared/lib/form";
import { ensureClientAccess } from "../../features/auth/session";

const EMPTY_CASE_STAGE = Object.freeze({
  label: "-",
  description: "-",
  showAIResult: false,
  primaryAction: Object.freeze({
    label: "-",
  }),
});

const EMPTY_CASE_CAPABILITIES = Object.freeze({
  actions: Object.freeze({
    canDownloadLatestReport: false,
    canUploadFiles: false,
  }),
  fields: Object.freeze({}),
});

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return fallback;
  }
  return parsed;
}

export default {
  components: {
    ClientTabBar,
    LongTaskStatusCard,
    PageStatusBanner,
  },
  data() {
    return {
      loading: false,
      caseId: 0,
      totalCases: 0,
      caseInfo: null,
      caseStage: EMPTY_CASE_STAGE,
      caseCapabilities: EMPTY_CASE_CAPABILITIES,
      currentUser: null,
      timeline: [],
      files: [],
      latestAnalysis: null,
      missingEvidenceHints: [],
      currentTask: null,
      wsConnected: false,
      reportDownloading: false,
      deletingFileId: 0,
    };
  },
  computed: {
    progressSteps() {
      return [
        { key: 'materials', label: '上传材料' },
        { key: 'reviewing', label: '律师整理' },
        { key: 'completed', label: '分析完成' },
      ]
    },
    progressLineFillStyle() {
      const idx = this.caseStage?.stepIndex ?? 0
      const pct = idx === 0 ? '0%' : idx === 1 ? '50%' : '100%'
      return `width: ${pct};`
    },
    stageFriendlyLabel() {
      const id = this.caseStage?.id
      const map = {
        awaiting_materials: '等待材料',
        uploading_materials: '上传中',
        upload_attention: '需要补传',
        reviewing_materials: '律师处理中',
        analysis_completed: '分析已完成',
        attention_needed: '需要关注',
      }
      return map[id] || this.caseStage?.label || '-'
    },
    stageFriendlyHint() {
      const id = this.caseStage?.id
      const map = {
        awaiting_materials: '请上传案件材料，律师收到后会开始整理。',
        uploading_materials: '文件正在上传，请稍等片刻。',
        upload_attention: '部分材料上传失败，请重新上传。',
        reviewing_materials: '律师正在整理你的材料，请耐心等待。',
        analysis_completed: 'AI 分析已完成，你可以在下方查看结果，或下载 PDF 报告。',
        attention_needed: '案件有异常，请联系负责律师确认。',
      }
      return map[id] || this.caseStage?.description || ''
    },
    stageBadgeClass() {
      const tone = this.caseStage?.tone
      const map = {
        neutral: 'badge-neutral',
        primary: 'badge-primary',
        warning: 'badge-warning',
        danger: 'badge-danger',
        success: 'badge-success',
      }
      return map[tone] || 'badge-neutral'
    },
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
      return Boolean(this.caseStage?.showAIResult);
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
    topFeedbackBanner() {
      return buildCaseTopFeedbackBanner({
        caseInfo: this.caseInfo,
        caseStage: this.caseStage,
      });
    },
    analysisTaskCard() {
      return buildCaseLongTaskCard({
        caseInfo: this.caseInfo,
        caseStage: this.caseStage,
        currentTask: this.currentTask,
        wsConnected: this.wsConnected,
      });
    },
  },
  onLoad(options) {
    const caseId = Number(options.id || options.caseId || 0);
    this.caseId = Number.isNaN(caseId) ? 0 : caseId;
  },
  onShow() {
    const user = ensureClientAccess();
    if (!user) {
      return;
    }
    this.currentUser = user;
    this.loadPage();
  },
  onUnload() {
    if (this.detailController) {
      this.detailController.dispose();
      this.detailController = null;
    }
  },
  methods: {
    handleTopFeedbackAction() {
      this.loadPage();
    },
    ensureDetailController() {
      if (!this.detailController) {
        this.detailController = createClientCaseDetailController();
      }
      return this.detailController;
    },
    applyControllerPatch(patch = {}) {
      const nextPatch = patch || {};
      const keys = [
        "loading",
        "caseId",
        "totalCases",
        "caseInfo",
        "caseStage",
        "caseCapabilities",
        "timeline",
        "files",
        "latestAnalysis",
        "missingEvidenceHints",
        "currentTask",
        "wsConnected",
      ];

      keys.forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(nextPatch, key)) {
          this[key] = nextPatch[key];
        }
      });
    },
    async loadPage() {
      try {
        await this.ensureDetailController().load({
          preferredCaseId: this.caseId,
          viewer: this.currentUser,
          onStateChange: (patch) => this.applyControllerPatch(patch),
        });
      } catch (error) {
        showFormError(friendlyError(error, "加载案件详情失败"));
      }
    },
    async previewFile(file) {
      if (!file?.capabilities?.actions?.canDownload) {
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
      if (!file?.capabilities?.actions?.canDownload) {
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
      if (!file?.capabilities?.actions?.canDelete || this.deletingFileId) {
        return;
      }
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "删除材料",
          content: `确定删除"${file.file_name}"吗？删除后无法恢复。`,
          confirmColor: "#dc2626",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
      if (!confirmed) {
        return;
      }

      this.deletingFileId = file.id;
      try {
        await filesApi.deleteFile(file.id);
        this.files = this.files.filter((f) => f.id !== file.id);
        uni.showToast({ title: "已删除", icon: "success" });
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
      if (!this.caseCapabilities.actions.canDownloadLatestReport) {
        showFormError("当前案件暂不支持下载报告");
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
      if (!this.caseCapabilities.actions.canUploadFiles) {
        showFormError("当前案件不允许继续上传材料");
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
.feedback-banner-wrap {
  margin-top: 20rpx;
  margin-bottom: 8rpx;
}

/* Progress step bar */
.progress-bar-card {
  margin: 16rpx 0 4rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 32rpx 28rpx 28rpx;
  box-shadow: 0 2rpx 12rpx rgba(15,23,42,0.06);
}

.progress-steps {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.progress-line-wrap {
  position: absolute;
  top: 28rpx;
  left: 52rpx;
  right: 52rpx;
  height: 4rpx;
  background: #e2e8f0;
  border-radius: 4rpx;
  z-index: 0;
}

.progress-line {
  position: absolute;
  inset: 0;
  background: #e2e8f0;
  border-radius: 4rpx;
}

.progress-line-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: #0ea5e9;
  border-radius: 4rpx;
  transition: width 0.3s ease;
}

.progress-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  position: relative;
  z-index: 1;
}

.step-dot {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-done .step-dot {
  background: #0ea5e9;
}

.step-active .step-dot {
  background: #0ea5e9;
  box-shadow: 0 0 0 6rpx rgba(14,165,233,0.18);
}

.step-pending .step-dot {
  background: #e2e8f0;
}

.step-dot-text {
  font-size: 22rpx;
  font-weight: 700;
  color: #fff;
}

.step-pending .step-dot-text {
  color: #94a3b8;
}

.step-label {
  font-size: 22rpx;
  font-weight: 500;
  color: #64748b;
  text-align: center;
}

.step-active .step-label {
  color: #0ea5e9;
  font-weight: 700;
}

.step-done .step-label {
  color: #0284c7;
}

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

.danger-action {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fff1f2;
}

/* Stage description */
.stage-desc-row {
  margin-top: 12rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.stage-desc-label {
  font-size: 22rpx;
  color: #94a3b8;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stage-desc-badge {
  display: inline-flex;
  align-self: flex-start;
  padding: 4rpx 16rpx;
  border-radius: 100rpx;
  font-size: 24rpx;
  font-weight: 600;
}

.badge-neutral { background: #f1f5f9; color: #475569; }
.badge-primary { background: #e0f2fe; color: #0369a1; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-danger  { background: #fee2e2; color: #b91c1c; }
.badge-success { background: #d1fae5; color: #065f46; }

.stage-desc-badge-text {
  font-size: 24rpx;
  font-weight: 600;
}

.stage-desc-hint {
  font-size: 24rpx;
  color: #64748b;
  line-height: 1.6;
}
</style>

