<template>
  <view class="upload-page">
    <view class="status-header">
      <text class="status-title">把材料传给律师</text>
      <text class="status-subtitle">{{ statusDesc }}</text>

      <view class="status-steps">
        <view v-for="(step, index) in steps" :key="step" class="step-item">
          <view
            class="step-dot"
            :class="{
              'step-dot-active': currentStep === index,
              'step-dot-done': currentStep > index,
            }"
          >
            <text class="step-dot-text">{{ currentStep > index ? "√" : index + 1 }}</text>
          </view>
          <text
            class="step-label"
            :class="{
              'step-label-active': currentStep === index,
              'step-label-done': currentStep > index,
            }"
          >
            {{ step }}
          </text>
          <view
            v-if="index < steps.length - 1"
            class="step-line"
            :class="{ 'step-line-done': currentStep > index }"
          ></view>
        </view>
      </view>

      <view class="status-meta">
        <text class="status-meta-line">案件：{{ caseTitleText }}</text>
        <text class="status-meta-line">法律类型：{{ legalTypeText }}</text>
        <text class="status-meta-line">业务阶段：{{ caseStage.label }}</text>
        <text class="status-meta-line">主动作：{{ caseStage.primaryAction.label }}</text>
        <text class="status-meta-line">解析状态：{{ analysisStatusText }}</text>
      </view>
    </view>

    <view v-if="topFeedbackBanner" class="section-banner">
      <page-status-banner
        :tone="topFeedbackBanner.tone"
        :title="topFeedbackBanner.title"
        :message="topFeedbackBanner.message"
        :action-label="topFeedbackBanner.actionLabel"
        @action="handleTopFeedbackAction"
      />
    </view>

    <view v-if="analysisTaskCard" class="section-block">
      <long-task-status-card
        :tone="analysisTaskCard.tone"
        :title="analysisTaskCard.title"
        :status-text="analysisTaskCard.statusText"
        :progress="analysisTaskCard.progress"
        :progress-text="analysisTaskCard.progressText"
        :message="analysisTaskCard.message"
        :hint="analysisTaskCard.hint"
        :action-label="analysisTaskCard.actionLabel"
        @action="loadCaseInfo"
      />
    </view>

    <view class="section-block guide-block" :class="{ 'guide-block-default': !caseInfo.upload_guide }">
      <view class="section-head">
        <text class="section-title">{{ caseInfo.upload_guide ? "律师提示" : "上传建议" }}</text>
      </view>
      <text class="guide-content">{{ caseInfo.upload_guide || defaultGuideText }}</text>
    </view>

    <view class="section-block">
      <view class="section-head">
        <text class="section-title">已上传材料</text>
        <text class="section-extra">{{ uploadedFiles.length }} 份</text>
      </view>
      <text class="section-desc">律师已收到的材料会显示在这里，你也可以随时继续补充。</text>

      <view v-if="pageLoading && !uploadedFiles.length" class="empty-state material-empty">
        <text class="empty-title">正在加载材料...</text>
      </view>

      <view v-else-if="!uploadedFiles.length" class="empty-state material-empty">
        <text class="empty-title">还没有上传任何材料</text>
        <text class="empty-hint">先从下方入口选择相册、拍照或文件开始上传。</text>
      </view>

      <view v-for="file in uploadedFiles" :key="file.id" class="material-card">
        <view class="material-kind">
          <text class="material-kind-text">{{ file.kindText }}</text>
        </view>

        <view class="material-main">
          <view class="material-top">
            <text class="material-name">{{ file.file_name }}</text>
            <text class="tag" :class="file.parseStatusClass">{{ file.parseStatusText }}</text>
          </view>
          <text class="material-meta">{{ file.createdAtText }} · {{ file.uploaderText }}</text>
          <text v-if="file.capabilities.fields.canViewDescription" class="material-desc">说明：{{ file.description }}</text>
          <text v-if="!file.capabilities.actions.canDownload" class="material-note">这份材料当前只展示名称，暂不支持直接预览或下载。</text>

          <view class="material-actions">
            <button class="mini-action" :disabled="!file.capabilities.actions.canDownload" @click="previewUploadedFile(file)">预览</button>
            <button class="mini-action" :disabled="!file.capabilities.actions.canDownload" @click="downloadUploadedFile(file)">下载</button>
            <button
              v-if="file.capabilities.actions.canDelete"
              class="mini-action mini-action-danger"
              :disabled="deletingFileId === file.id || isAnyUploading"
              @click="deleteUploadedFile(file)"
            >
              删除
            </button>
          </view>
        </view>
      </view>
    </view>

    <view class="section-block">
      <view class="section-head">
        <text class="section-title">上传入口</text>
        <text v-if="selectedFiles.length" class="section-extra">队列中 {{ selectedFiles.length }} 份</text>
      </view>
      <text class="section-desc">建议按“批次 + 主题”上传（如：立案材料一批、聊天记录一批、转账凭证一批），方便律师和 AI 快速理解。</text>

      <view class="upload-actions">
        <view class="entry-button" :class="{ 'entry-button-disabled': isAnyUploading || !caseCapabilities.actions.canUploadFiles }" @click="chooseFromAlbum">
          <text class="entry-title">从相册选择</text>
          <text class="entry-hint">一次可选多张照片</text>
        </view>
        <view class="entry-button" :class="{ 'entry-button-disabled': isAnyUploading || !caseCapabilities.actions.canUploadFiles }" @click="takePhoto">
          <text class="entry-title">拍照上传</text>
          <text class="entry-hint">适合纸质材料</text>
        </view>
        <view class="entry-button" :class="{ 'entry-button-disabled': isAnyUploading || !caseCapabilities.actions.canUploadFiles }" @click="chooseMessageFiles">
          <text class="entry-title">上传文件</text>
          <text class="entry-hint">支持常见文档格式</text>
        </view>
      </view>

      <text class="upload-hint">支持 JPG、PNG、PDF、Word、Excel 等常见材料；单份不超过 20MB；建议同类材料成批上传并在“材料说明/补充说明”写清这批材料证明什么；检测到疑似重复材料时会先提醒你确认。</text>

      <upload-failure-notice
        v-if="uploadFailureFeedback"
        :title="uploadFailureFeedback.title"
        :message="uploadFailureFeedback.message"
        :action-label="uploadFailureFeedback.actionLabel"
        :disabled="isAnyUploading || !caseCapabilities.actions.canUploadFiles"
        @retry="submitAll"
      />

      <view v-if="selectedFiles.length" class="queue-block">
        <view class="queue-head">
          <text class="queue-title">待上传队列</text>
          <text class="queue-subtitle">建议按同一批次填写同一主题，便于后续回看与重分析</text>
        </view>

        <view
          v-for="(item, index) in selectedFiles"
          :key="item.uid"
          class="queue-card"
          :class="{
            'queue-card-uploading': item.status === 'uploading',
            'queue-card-failed': item.status === 'failed',
            'queue-card-success': item.status === 'success',
          }"
        >
          <view class="queue-main">
            <view class="material-top">
              <text class="material-name">{{ item.name }}</text>
              <text class="tag" :class="item.statusTagClass">{{ item.statusText }}</text>
            </view>
            <text class="queue-meta">来源：{{ item.sourceText }}</text>
            <text class="queue-desc-label">材料说明 <text class="queue-desc-hint">（帮律师快速理解这份材料）</text></text>
            <input
              v-model="item.description"
              class="queue-input"
              :class="{ 'queue-input-empty': submitAttempted && !item.description.trim() && item.status !== 'uploading' }"
              maxlength="200"
              :disabled="item.status === 'uploading'"
              :placeholder="descriptionPlaceholder(item)"
            />

            <view v-if="item.status !== 'waiting'" class="queue-progress">
              <view class="queue-progress-track">
                <view
                  class="queue-progress-fill"
                  :class="{
                    'queue-progress-fill-success': item.status === 'success',
                    'queue-progress-fill-failed': item.status === 'failed',
                  }"
                  :style="{ width: `${item.progress}%` }"
                ></view>
              </view>
              <text class="queue-progress-text">{{ item.progressText }}</text>
            </view>

            <text v-if="item.error" class="queue-error">{{ item.error }}</text>
          </view>

          <view class="queue-side">
            <button
              v-if="item.status === 'failed'"
              class="mini-action"
              :disabled="isAnyUploading"
              @click="retrySingleFile(item.uid)"
            >
              重试
            </button>
            <button
              class="mini-action"
              :disabled="item.status === 'uploading' || isAnyUploading"
              @click="removeFile(index)"
            >
              移除
            </button>
          </view>
        </view>
      </view>

      <button
        class="primary-upload-btn"
        :disabled="!pendingQueueCount || isAnyUploading || !caseCapabilities.actions.canUploadFiles"
        :loading="submitting"
        @click="submitAll"
      >
        {{ submitButtonText }}
      </button>
    </view>

    <view v-if="caseCapabilities.actions.canEditClientRemark" class="section-block">
      <CaseRemarkInput
        title="补充说明"
        hint="会同步给律师和 AI，帮助理解材料背景"
        placeholder="如有关键时间点、沟通背景、你的诉求或需要律师注意的情况，可在这里补充..."
        submit-label="保存说明"
        existing-label="已保存说明"
        :show-voice="true"
        :max-length="2000"
        :existing-remark="caseInfo.client_remark"
        :submit-handler="handleRemarkSubmit"
        success-text="说明已保存"
      />
    </view>

    <view class="privacy-note">
      <text class="privacy-text">你上传的材料仅对本案相关律师可见；你可随时删除自己上传的文件；如包含与案件无关的隐私信息，建议先遮挡后再上传。</text>
    </view>

    <client-tab-bar current-key="cases" />
  </view>
</template>

<script>
import CaseRemarkInput from "../../components/CaseRemarkInput.vue";
import ClientTabBar from "../../components/ClientTabBar.vue";
import LongTaskStatusCard from "../../components/LongTaskStatusCard.vue";
import PageStatusBanner from "../../components/PageStatusBanner.vue";
import UploadFailureNotice from "../../components/UploadFailureNotice.vue";
import { appendClientRemarkPreview, getCaseDetail, getRemarkValue, updateClientRemark } from "../../features/cases/api";
import {
  buildCaseLongTaskCard,
  buildCaseTopFeedbackBanner,
  buildUploadFailureFeedback,
} from "../../features/cases/feedback";
import { filesApi } from "../../shared/api/domain-api";
import { createUploadSessionController } from "../../features/cases/upload-session-controller";
import {
  buildCaseCapabilities,
  buildCaseFileCapabilities,
  CLIENT_CASE_STAGE_STEPS,
  resolveCaseStage,
} from "../../entities/case/policy";
import { downloadCaseFile, previewCaseFile } from "../../shared/lib/file";
import { formatAnalysisStatus, formatDateTime, formatLegalType } from "../../shared/lib/display";
import { friendlyError, showFormError } from "../../shared/lib/form";
import { ensureClientAccess, redirectByRole } from "../../features/auth/session";

const DEFAULT_GUIDE_TEXT =
  "请将所有与案件相关的照片、文件、截图都先上传上来。不确定是否需要的材料也可以先上传，律师会帮你判断。";

function createEmptyCaseInfo() {
  return {
    title: "",
    legal_type: "",
    analysis_status: "not_started",
    analysis_progress: 0,
    client_remark: "",
    upload_guide: "",
  };
}

function parseStatusText(value) {
  const map = {
    pending: "待整理",
    processing: "整理中",
    completed: "已整理",
    failed: "整理失败",
  };
  return map[String(value || "").toLowerCase()] || "已收到";
}

function parseStatusClass(value) {
  const map = {
    pending: "tag-neutral",
    processing: "tag-primary",
    completed: "tag-success",
    failed: "tag-danger",
  };
  return map[String(value || "").toLowerCase()] || "tag-neutral";
}

function fileKindText(file) {
  const name = String(file?.file_name || "").toLowerCase();
  const type = String(file?.file_type || "").toLowerCase();

  if (type.startsWith("image/") || /\.(png|jpg|jpeg|gif|webp)$/.test(name)) {
    return "图片";
  }
  if (name.endsWith(".pdf") || type.includes("pdf")) {
    return "PDF";
  }
  if (/\.(doc|docx)$/.test(name) || type.includes("word")) {
    return "文档";
  }
  if (/\.(xls|xlsx)$/.test(name) || type.includes("excel") || type.includes("sheet")) {
    return "表格";
  }
  return "文件";
}

function uploaderText(file) {
  const role = String(file?.uploader_role || "").toLowerCase();
  if (role === "client") {
    return "你上传";
  }
  if (role === "lawyer") {
    return "律师整理";
  }
  return "系统记录";
}

export default {
  components: {
    CaseRemarkInput,
    ClientTabBar,
    LongTaskStatusCard,
    PageStatusBanner,
    UploadFailureNotice,
  },
  data() {
    return {
      steps: CLIENT_CASE_STAGE_STEPS,
      defaultGuideText: DEFAULT_GUIDE_TEXT,
      caseId: 0,
      caseInfo: createEmptyCaseInfo(),
      currentUser: null,
      uploadedFiles: [],
      selectedFiles: [],
      pageLoading: false,
      submitting: false,
      deletingFileId: 0,
      uploadSessionNotice: "",
      networkOnline: true,
      networkNoticeText: "",
      autoResumePending: false,
      networkChangeHandler: null,
      networkMonitorAttached: false,
      submitAttempted: false,
    };
  },
  computed: {
    caseTitleText() {
      return this.caseInfo.title || `案件 #${this.caseId}`;
    },
    waitingCount() {
      return this.selectedFiles.filter((item) => item.status === "waiting").length;
    },
    uploadingCount() {
      return this.selectedFiles.filter((item) => item.status === "uploading").length;
    },
    failedCount() {
      return this.selectedFiles.filter((item) => item.status === "failed").length;
    },
    pendingQueueCount() {
      return this.selectedFiles.filter((item) => ["waiting", "failed"].includes(item.status)).length;
    },
    missingDescriptionCount() {
      return this.selectedFiles.filter(
        (item) => ["waiting", "failed"].includes(item.status) && !item.description.trim()
      ).length;
    },
    isAnyUploading() {
      return this.uploadingCount > 0 || this.submitting;
    },
    submitButtonText() {
      if (this.isAnyUploading) {
        const count = this.uploadingCount || this.pendingQueueCount || 1;
        return `正在上传 ${count} 份材料`;
      }
      if (!this.networkOnline && this.pendingQueueCount > 0) {
        return "当前离线，请联网后上传";
      }
      if (this.failedCount > 0 && this.waitingCount > 0) {
        return `继续上传剩余 ${this.pendingQueueCount} 份材料`;
      }
      if (this.failedCount > 0) {
        return this.failedCount === 1 ? "重试失败材料" : `重试 ${this.failedCount} 份失败材料`;
      }
      if (this.pendingQueueCount > 0) {
        return `开始上传 ${this.pendingQueueCount} 份材料`;
      }
      return "请先选择材料";
    },
    activeNetworkNotice() {
      if (this.networkNoticeText) {
        return this.networkNoticeText;
      }
      if (!this.networkOnline) {
        if (this.pendingQueueCount > 0) {
          return "当前网络不可用，已选材料会先保留在队列里，请在网络恢复后继续上传。";
        }
        return "当前网络不可用，请切换到稳定网络后再开始上传。";
      }
      return "";
    },
    caseStage() {
      return resolveCaseStage(this.caseInfo, {
        hasUploadedFiles: this.uploadedFiles.length > 0,
        pendingUploads: this.waitingCount,
        failedUploads: this.failedCount,
        uploadingCount: this.uploadingCount,
      });
    },
    caseCapabilities() {
      return buildCaseCapabilities({
        viewer: this.currentUser,
        caseItem: this.caseInfo,
        stage: this.caseStage,
      });
    },
    currentStep() {
      return this.caseStage.stepIndex;
    },
    statusDesc() {
      if (this.activeNetworkNotice && (!this.networkOnline || this.autoResumePending)) {
        return this.activeNetworkNotice;
      }
      if (this.uploadSessionNotice) {
        return this.uploadSessionNotice;
      }
      return this.caseStage.description;
    },
    analysisStatusText() {
      return formatAnalysisStatus(this.caseInfo.analysis_status, this.caseInfo.analysis_progress);
    },
    legalTypeText() {
      return formatLegalType(this.caseInfo.legal_type || "");
    },
    topFeedbackBanner() {
      return buildCaseTopFeedbackBanner({
        caseInfo: this.caseInfo,
        caseStage: this.caseStage,
        networkNoticeText: this.activeNetworkNotice,
        uploadSessionNotice: this.uploadSessionNotice,
        failedCount: this.failedCount,
        pendingQueueCount: this.pendingQueueCount,
        autoResumePending: this.autoResumePending,
        canUploadFiles: this.caseCapabilities.actions.canUploadFiles,
      });
    },
    analysisTaskCard() {
      return buildCaseLongTaskCard({
        caseInfo: this.caseInfo,
        caseStage: this.caseStage,
      });
    },
    uploadFailureFeedback() {
      return buildUploadFailureFeedback({
        failedCount: this.failedCount,
        pendingQueueCount: this.pendingQueueCount,
        autoResumePending: this.autoResumePending,
      });
    },
  },
  onLoad(options) {
    const user = ensureClientAccess();
    if (!user) {
      return;
    }

    this.currentUser = user;
    const caseId = Number(options.caseId || options.id || 0);
    if (!caseId) {
      showFormError("缺少案件参数");
      redirectByRole(user);
      return;
    }

    this.caseId = caseId;
    this.ensureUploadSessionController();
    this.setupNetworkMonitor();
    this.loadPage();
  },
  onUnload() {
    this.teardownNetworkMonitor();
    if (this.uploadSessionController) {
      this.uploadSessionController.dispose();
      this.uploadSessionController = null;
    }
  },
  async onPullDownRefresh() {
    try {
      await this.loadPage();
    } finally {
      uni.stopPullDownRefresh();
    }
  },
  methods: {
    descriptionPlaceholder(item) {
      const ext = String(item.extension || "").toLowerCase();
      const source = String(item.sourceText || "").toLowerCase();
      if (source.includes("拍照") || source.includes("camera")) {
        return "说一下这张照片是什么，例如：事发当天现场照片";
      }
      if (/^(png|jpg|jpeg|gif|webp|heic)$/.test(ext) || source.includes("相册") || source.includes("图片")) {
        return "说一下这张图片是什么，例如：转账记录截图";
      }
      if (ext === "pdf") {
        return "说一下这份文件是什么，例如：签署的合同或协议";
      }
      if (/^(doc|docx)$/.test(ext)) {
        return "说一下这份文件是什么，例如：起诉状或证明材料";
      }
      if (/^(xls|xlsx|csv)$/.test(ext)) {
        return "说一下这份表格是什么，例如：工资流水或账目记录";
      }
      return "说一下这是什么材料，帮律师快速理解";
    },
    async handleTopFeedbackAction() {
      if (this.failedCount > 0 && this.caseCapabilities.actions.canUploadFiles) {
        await this.submitAll();
        return;
      }
      try {
        await this.loadCaseInfo();
      } catch (error) {
        showFormError(friendlyError(error, "刷新状态失败"));
      }
    },
    ensureUploadSessionController() {
      if (!this.uploadSessionController) {
        this.uploadSessionController = createUploadSessionController();
        this.uploadSessionController.setHandler((patch) => this.applyUploadSessionPatch(patch));
      }
      return this.uploadSessionController;
    },
    applyUploadSessionPatch(patch = {}) {
      const nextPatch = patch || {};
      ["selectedFiles", "submitting", "uploadSessionNotice", "autoResumePending"].forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(nextPatch, key)) {
          this[key] = nextPatch[key];
        }
      });
    },
    setupNetworkMonitor() {
      if (this.networkMonitorAttached) {
        return;
      }

      this.refreshNetworkState();
      this.networkChangeHandler = (result) => {
        this.handleNetworkChange(result);
      };

      if (typeof uni.onNetworkStatusChange === "function") {
        uni.onNetworkStatusChange(this.networkChangeHandler);
        this.networkMonitorAttached = true;
      }
    },
    teardownNetworkMonitor() {
      if (
        this.networkMonitorAttached &&
        this.networkChangeHandler &&
        typeof uni.offNetworkStatusChange === "function"
      ) {
        uni.offNetworkStatusChange(this.networkChangeHandler);
      }
      this.networkChangeHandler = null;
      this.networkMonitorAttached = false;
    },
    refreshNetworkState() {
      if (typeof uni.getNetworkType !== "function") {
        return;
      }
      uni.getNetworkType({
        success: (result) => {
          this.handleNetworkChange(result);
        },
      });
    },
    handleNetworkChange(result = {}) {
      const networkType = String(result.networkType || "").toLowerCase();
      const isConnected =
        typeof result.isConnected === "boolean"
          ? result.isConnected && networkType !== "none"
          : networkType
            ? networkType !== "none" && networkType !== "unknown"
            : this.networkOnline;
      const wasOnline = this.networkOnline;

      this.networkOnline = isConnected;
      if (!isConnected) {
        this.networkNoticeText =
          this.isAnyUploading || this.pendingQueueCount > 0 || this.autoResumePending
            ? "当前网络不稳定，未完成的材料会先保留，网络恢复后可继续上传。"
            : "当前网络不可用，请切换到稳定网络后再上传。";
        return;
      }

      if (!wasOnline && this.autoResumePending && this.pendingQueueCount > 0 && !this.isAnyUploading) {
        this.networkNoticeText = "网络已恢复，正在继续上传刚才未完成的材料。";
        this.autoResumePending = false;
        Promise.resolve()
          .then(() => this.continuePendingUploads({ skipConfirm: true, silent: true }))
          .catch(() => {});
        return;
      }

      if (!wasOnline && this.pendingQueueCount > 0) {
        this.networkNoticeText = "网络已恢复，可以继续上传待处理材料。";
        return;
      }

      if (!this.autoResumePending) {
        this.networkNoticeText = "";
      }
    },
    decorateUploadedFiles(items) {
      return (Array.isArray(items) ? items : []).map((file) => ({
        ...file,
        kindText: fileKindText(file),
        parseStatusText: parseStatusText(file.parse_status),
        parseStatusClass: parseStatusClass(file.parse_status),
        createdAtText: formatDateTime(file.created_at, "-"),
        uploaderText: uploaderText(file),
        capabilities: buildCaseFileCapabilities({
          viewer: this.currentUser,
          caseItem: this.caseInfo,
          fileItem: file,
          caseCapabilities: this.caseCapabilities,
        }),
      }));
    },
    async loadCaseInfo() {
      const detail = await getCaseDetail(this.caseId);
      this.caseInfo = {
        ...createEmptyCaseInfo(),
        ...(detail || {}),
      };
      if (this.uploadedFiles.length) {
        this.uploadedFiles = this.decorateUploadedFiles(this.uploadedFiles);
      }
    },
    async loadUploadedFiles() {
      const files = await filesApi.listCaseFiles(this.caseId);
      this.uploadedFiles = this.decorateUploadedFiles(files);
    },
    async loadPage() {
      if (!this.caseId) {
        return;
      }

      this.pageLoading = true;
      try {
        await Promise.all([this.loadCaseInfo(), this.loadUploadedFiles()]);
      } catch (error) {
        showFormError(friendlyError(error, "加载页面失败"));
      } finally {
        this.pageLoading = false;
      }
    },
    async handleRemarkSubmit(text) {
      if (!this.caseCapabilities.actions.canEditClientRemark) {
        throw { message: "当前案件不允许修改补充说明" };
      }
      const detail = await updateClientRemark(this.caseId, text);
      const nextRemark =
        getRemarkValue(detail, "client_remark") ||
        appendClientRemarkPreview(this.caseInfo.client_remark, text);

      this.caseInfo = {
        ...(this.caseInfo || {}),
        ...(detail || {}),
        client_remark: nextRemark,
      };
      return detail;
    },
    applyPostUploadCaseState() {
      this.caseInfo = {
        ...(this.caseInfo || {}),
        analysis_status: "pending_reanalysis",
        analysis_progress: 0,
      };
    },
    upsertUploadedFile(file) {
      const decorated = this.decorateUploadedFiles([file])[0];
      if (!decorated) {
        return;
      }

      const nextFiles = this.uploadedFiles.filter((item) => item.id !== decorated.id);
      nextFiles.unshift(decorated);
      this.uploadedFiles = nextFiles;
    },
    showSingleActionModal(title, content) {
      return new Promise((resolve) => {
        uni.showModal({
          title,
          content,
          showCancel: false,
          success: () => resolve(),
          fail: () => resolve(),
        });
      });
    },
    confirmDuplicateFiles(content) {
      return new Promise((resolve) => {
        uni.showModal({
          title: "检测到疑似重复材料",
          content,
          confirmText: "仍然加入",
          cancelText: "跳过重复",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
    },
    confirmUpload() {
      return new Promise((resolve) => {
        uni.showModal({
          title: "确认上传",
          content: "上传后律师会收到这些材料，并继续整理案件。是否继续？",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
    },
    async appendFiles(files, sourceText) {
      if (!Array.isArray(files) || !files.length || this.isAnyUploading) {
        return;
      }

      await this.ensureUploadSessionController().appendFiles({
        files,
        sourceText,
        uploadedFiles: this.uploadedFiles,
        onInvalidFiles: (message) => this.showSingleActionModal("已跳过部分材料", message),
        onConfirmDuplicates: (message) => this.confirmDuplicateFiles(message),
      });

      this.submitAttempted = false;

      if (this.networkOnline && !this.autoResumePending) {
        this.networkNoticeText = "";
      }
    },
    chooseFromAlbum() {
      if (!this.caseCapabilities.actions.canUploadFiles) {
        showFormError("当前案件不允许继续上传材料");
        return;
      }
      if (this.isAnyUploading) {
        return;
      }

      uni.chooseImage({
        count: 20,
        sizeType: ["original", "compressed"],
        sourceType: ["album"],
        success: ({ tempFiles = [], tempFilePaths = [] }) => {
          const files = tempFiles.length
            ? tempFiles
            : tempFilePaths.map((path, index) => ({ path, name: `image-${index + 1}.jpg` }));
          this.appendFiles(files, "相册图片");
        },
        fail: (error) => {
          showFormError(friendlyError(error, "选择相册图片失败"));
        },
      });
    },
    takePhoto() {
      if (!this.caseCapabilities.actions.canUploadFiles) {
        showFormError("当前案件不允许继续上传材料");
        return;
      }
      if (this.isAnyUploading) {
        return;
      }

      uni.chooseImage({
        count: 9,
        sizeType: ["original", "compressed"],
        sourceType: ["camera"],
        success: ({ tempFiles = [], tempFilePaths = [] }) => {
          const files = tempFiles.length
            ? tempFiles
            : tempFilePaths.map((path, index) => ({ path, name: `camera-${index + 1}.jpg` }));
          this.appendFiles(files, "拍照上传");
        },
        fail: (error) => {
          showFormError(friendlyError(error, "拍照失败"));
        },
      });
    },
    chooseMessageFiles() {
      if (!this.caseCapabilities.actions.canUploadFiles) {
        showFormError("当前案件不允许继续上传材料");
        return;
      }
      if (this.isAnyUploading) {
        return;
      }

      uni.chooseMessageFile({
        count: 20,
        type: "file",
        success: ({ tempFiles = [] }) => {
          this.appendFiles(tempFiles, "聊天或本地文件");
        },
        fail: (error) => {
          showFormError(friendlyError(error, "选择文件失败"));
        },
      });
    },
    removeFile(index) {
      this.ensureUploadSessionController().removeFile(index);
    },
    handleUploadCommit(uploaded) {
      this.applyPostUploadCaseState();
      this.upsertUploadedFile(uploaded);
    },
    applyUploadControllerResult(result = {}, { silent = false } = {}) {
      if (!result || typeof result !== "object") {
        return;
      }

      if (Object.prototype.hasOwnProperty.call(result, "networkNoticeText")) {
        this.networkNoticeText = result.networkNoticeText || "";
      } else if (this.networkOnline && !this.autoResumePending) {
        this.networkNoticeText = "";
      }

      if (!silent && result.errorMessage) {
        showFormError(result.errorMessage);
      }

      if (result.successToastText) {
        uni.showToast({
          title: result.successToastText,
          icon: "success",
        });
      }
    },
    async retrySingleFile(uid) {
      const result = await this.ensureUploadSessionController().retrySingleFile({
        uid,
        caseId: this.caseId,
        networkOnline: this.networkOnline,
        onFileUploaded: async (uploaded) => this.handleUploadCommit(uploaded),
        onReloadCaseInfo: async () => this.loadCaseInfo(),
      });
      this.applyUploadControllerResult(result);
    },
    async continuePendingUploads({ skipConfirm = false, silent = false } = {}) {
      const result = await this.ensureUploadSessionController().continuePendingUploads({
        caseId: this.caseId,
        canUploadFiles: this.caseCapabilities.actions.canUploadFiles,
        networkOnline: this.networkOnline,
        skipConfirm,
        silent,
        confirmUpload: () => this.confirmUpload(),
        onFileUploaded: async (uploaded) => this.handleUploadCommit(uploaded),
        onReloadCaseInfo: async () => this.loadCaseInfo(),
      });
      this.applyUploadControllerResult(result, { silent });
      return result;
    },
    async submitAll() {
      const missingCount = this.missingDescriptionCount;
      if (missingCount > 0) {
        this.submitAttempted = true;
        const proceed = await this.confirmMissingDescriptions(missingCount);
        if (!proceed) {
          return;
        }
      }
      const result = await this.continuePendingUploads();
      if (result && result.successCount > 0 && result.remainingCount === 0) {
        await new Promise((resolve) => {
          uni.showModal({
            title: '材料已发送给律师 ✓',
            content: `共 ${result.successCount} 份材料已成功上传。律师收到后会开始整理，你可以随时回来查看进展或补充材料。`,
            showCancel: false,
            confirmText: '好的，返回案件',
            success: () => resolve(),
          });
        });
        uni.navigateBack();
      }
    },
    confirmMissingDescriptions(count) {
      return new Promise((resolve) => {
        uni.showModal({
          title: "有材料还没填说明",
          content: `还有 ${count} 份材料没有填写说明。建议按“批次 + 主题”补充说明（例如：聊天记录一批，证明双方沟通经过），这会显著提升律师处理和 AI 重分析效率。\n\n现在直接上传也可以。`,
          confirmText: "直接上传",
          cancelText: "返回补充",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
    },
    async previewUploadedFile(file) {
      if (!file?.capabilities?.actions?.canDownload) {
        showFormError("这份材料当前不支持直接预览");
        return;
      }

      try {
        await previewCaseFile(file);
      } catch (error) {
        showFormError(friendlyError(error, "文件预览失败"));
      }
    },
    async downloadUploadedFile(file) {
      if (!file?.capabilities?.actions?.canDownload) {
        showFormError("这份材料当前不支持直接下载");
        return;
      }

      try {
        await downloadCaseFile(file);
      } catch (error) {
        showFormError(friendlyError(error, "文件下载失败"));
      }
    },
    async deleteUploadedFile(file) {
      if (!file?.capabilities?.actions?.canDelete || this.deletingFileId) {
        return;
      }
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "删除材料",
          content: `确定删除“${file.file_name}”吗？删除后无法恢复。`,
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
        this.uploadedFiles = this.uploadedFiles.filter((item) => item.id !== file.id);
        uni.showToast({
          title: "已删除",
          icon: "success",
        });
        try {
          await this.loadCaseInfo();
        } catch {
          // Keep local state when refresh fails.
        }
      } catch (error) {
        showFormError(friendlyError(error, "删除材料失败"));
      } finally {
        this.deletingFileId = 0;
      }
    },
  },
};
</script>

<style scoped>
.upload-page {
  min-height: 100vh;
  background: #f4f7fb;
  padding-bottom: calc(140rpx + env(safe-area-inset-bottom));
}

.status-header {
  padding: 40rpx 28rpx 32rpx;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
  color: #fff;
}

.status-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
}

.status-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 26rpx;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.88);
}

.status-steps {
  display: flex;
  align-items: center;
  margin-top: 28rpx;
  overflow: hidden;
}

.step-item {
  display: flex;
  align-items: center;
  min-width: 0;
}

.step-dot {
  width: 44rpx;
  height: 44rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-dot-active {
  background: #ffffff;
}

.step-dot-done {
  background: #22c55e;
}

.step-dot-text {
  color: #ffffff;
  font-size: 22rpx;
  font-weight: 700;
}

.step-dot-active .step-dot-text {
  color: #1d4ed8;
}

.step-label {
  margin: 0 10rpx;
  color: rgba(255, 255, 255, 0.72);
  font-size: 22rpx;
  white-space: nowrap;
}

.step-label-active,
.step-label-done {
  color: #ffffff;
}

.step-line {
  width: 44rpx;
  height: 2rpx;
  margin-right: 10rpx;
  background: rgba(255, 255, 255, 0.25);
}

.step-line-done {
  background: rgba(255, 255, 255, 0.78);
}

.status-meta {
  margin-top: 24rpx;
  padding: 20rpx 22rpx;
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.12);
}

.status-meta-line {
  display: block;
  color: rgba(255, 255, 255, 0.88);
  font-size: 24rpx;
  line-height: 1.7;
}

.section-banner {
  margin: 20rpx 24rpx 0;
}

.section-block {
  margin: 20rpx 24rpx 0;
  padding: 24rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 10rpx 30rpx rgba(15, 23, 42, 0.05);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #0f172a;
}

.section-extra {
  font-size: 24rpx;
  color: #64748b;
}

.section-desc {
  display: block;
  margin-top: 10rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.7;
}

.guide-block {
  background: #fff9db;
}

.guide-block-default {
  background: #eff6ff;
}

.guide-content {
  display: block;
  margin-top: 12rpx;
  color: #334155;
  font-size: 28rpx;
  line-height: 1.8;
  white-space: pre-wrap;
}

.material-empty {
  padding-top: 32rpx;
}

.empty-title {
  display: block;
  color: #334155;
  font-size: 28rpx;
  font-weight: 600;
}

.empty-hint {
  display: block;
  margin-top: 8rpx;
  color: #94a3b8;
  font-size: 24rpx;
  line-height: 1.7;
}

.material-card,
.queue-card {
  display: flex;
  gap: 18rpx;
  padding: 20rpx 0;
  border-top: 1rpx solid #eef2f7;
}

.material-kind {
  width: 88rpx;
  height: 88rpx;
  border-radius: 20rpx;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.material-kind-text {
  color: #2563eb;
  font-size: 24rpx;
  font-weight: 700;
}

.material-main,
.queue-main {
  flex: 1;
  min-width: 0;
}

.material-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}

.material-name {
  flex: 1;
  min-width: 0;
  color: #0f172a;
  font-size: 28rpx;
  font-weight: 600;
  line-height: 1.6;
  word-break: break-all;
}

.material-meta,
.material-desc,
.material-note,
.queue-meta {
  display: block;
  margin-top: 8rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.7;
}

.material-note {
  color: #b45309;
}

.material-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 14rpx;
}

.upload-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 22rpx;
}

.entry-button {
  flex: 1;
  min-height: 164rpx;
  padding: 24rpx 16rpx;
  border-radius: 22rpx;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
}

.entry-button-disabled {
  opacity: 0.6;
}

.entry-title {
  color: #1e293b;
  font-size: 28rpx;
  font-weight: 600;
  text-align: center;
}

.entry-hint {
  color: #64748b;
  font-size: 22rpx;
  line-height: 1.6;
  text-align: center;
}

.upload-hint {
  display: block;
  margin-top: 16rpx;
  color: #94a3b8;
  font-size: 22rpx;
  line-height: 1.7;
}

.queue-block {
  margin-top: 20rpx;
  border-top: 1rpx solid #eef2f7;
}

.queue-head {
  padding-top: 18rpx;
}

.queue-title {
  display: block;
  color: #0f172a;
  font-size: 28rpx;
  font-weight: 600;
}

.queue-subtitle {
  display: block;
  margin-top: 6rpx;
  color: #64748b;
  font-size: 22rpx;
}

.queue-card-uploading {
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.03) 0%, rgba(37, 99, 235, 0) 100%);
}

.queue-card-failed {
  background: linear-gradient(180deg, rgba(220, 38, 38, 0.04) 0%, rgba(220, 38, 38, 0) 100%);
}

.queue-card-success {
  background: linear-gradient(180deg, rgba(34, 197, 94, 0.04) 0%, rgba(34, 197, 94, 0) 100%);
}

.queue-side {
  width: 140rpx;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12rpx;
}

.queue-input {
  width: 100%;
  min-height: 78rpx;
  margin-top: 12rpx;
  padding: 18rpx 20rpx;
  border-radius: 18rpx;
  background: #f8fafc;
  color: #0f172a;
  font-size: 26rpx;
  box-sizing: border-box;
  border: 2rpx solid transparent;
}

.queue-input-empty {
  border-color: #f97316;
  background: #fff7ed;
}

.queue-desc-label {
  display: block;
  margin-top: 14rpx;
  color: #334155;
  font-size: 24rpx;
  font-weight: 600;
}

.queue-desc-hint {
  color: #94a3b8;
  font-weight: 400;
  font-size: 22rpx;
}

.queue-progress {
  margin-top: 14rpx;
}
.queue-progress-track {
  width: 100%;
  height: 10rpx;
  border-radius: 999rpx;
  background: #e2e8f0;
  overflow: hidden;
}

.queue-progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
}

.queue-progress-fill-success {
  background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
}

.queue-progress-fill-failed {
  background: linear-gradient(90deg, #f97316 0%, #ef4444 100%);
}

.queue-progress-text {
  display: block;
  margin-top: 8rpx;
  color: #475569;
  font-size: 22rpx;
}

.queue-error {
  display: block;
  margin-top: 8rpx;
  color: #dc2626;
  font-size: 24rpx;
  line-height: 1.6;
}

.primary-upload-btn {
  width: 100%;
  margin-top: 22rpx;
  border-radius: 20rpx;
  background: #2563eb;
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 600;
}

.privacy-note {
  margin: 20rpx 24rpx 0;
  padding: 18rpx 22rpx;
  border-radius: 20rpx;
  background: #f0fdf4;
}

.privacy-text {
  display: block;
  color: #166534;
  font-size: 22rpx;
  line-height: 1.7;
}

.mini-action,
.primary-upload-btn {
  box-sizing: border-box;
}

.mini-action {
  min-width: 112rpx;
  height: 60rpx;
  line-height: 60rpx;
  padding: 0 20rpx;
  border-radius: 999rpx;
  background: #f8fafc;
  color: #2563eb;
  font-size: 22rpx;
}

.mini-action-danger {
  color: #dc2626;
}

.mini-action::after,
.primary-upload-btn::after {
  display: none;
}
</style>

