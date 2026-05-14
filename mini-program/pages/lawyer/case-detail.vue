<template>
  <view class="page-container workspace-page">
    <view class="card" v-if="caseInfo">
      <text class="section-title">{{ caseInfo.title }}</text>
      <text class="meta">案号：{{ caseInfo.case_number }}</text>
      <text class="meta">业务阶段：{{ caseStage.label }}</text>
      <text class="meta">主动作：{{ caseStage.primaryAction.label }}</text>
      <text class="meta">当事人：{{ formatText(caseInfo.client ? caseInfo.client.real_name : "", "未关联") }}</text>
      <button v-if="caseCapabilities.actions.canGenerateInvite" class="primary-btn" :disabled="inviteLoading" :loading="inviteLoading" @click="loadInvite">{{ inviteLoading ? "生成中..." : "生成当事人邀请" }}</button>
      <view v-if="caseCapabilities.actions.canGenerateInvite && invitePath" class="invite-box">
        <text class="invite-label">邀请路径</text>
        <text class="meta invite-tip">把这条路径发给当事人，对方进入小程序后可直接绑定到当前案件。</text>
        <text class="invite-path">{{ invitePath }}</text>
        <button class="ghost-btn" @click="copyInvitePath">复制路径</button>
      </view>
    </view>

    <view v-if="topFeedbackBanner" class="card">
      <page-status-banner
        :tone="topFeedbackBanner.tone"
        :title="topFeedbackBanner.title"
        :message="topFeedbackBanner.message"
        :action-label="topFeedbackBanner.actionLabel"
        @action="loadCaseDetail"
      />
    </view>

    <view v-if="analysisTaskCard" class="card">
      <long-task-status-card
        :tone="analysisTaskCard.tone"
        :title="analysisTaskCard.title"
        :status-text="analysisTaskCard.statusText"
        :progress="analysisTaskCard.progress"
        :progress-text="analysisTaskCard.progressText"
        :message="analysisTaskCard.message"
        :hint="analysisTaskCard.hint"
        :action-label="analysisTaskCard.actionLabel"
        @action="loadCaseDetail"
      />
    </view>

    <view v-if="caseCapabilities.fields.canViewUploadGuide && caseInfo && caseInfo.upload_guide" class="card">
      <text class="section-title">当事人上传指引</text>
      <text class="meta">这段内容会显示在当事人补充材料页顶部，用于减少对方上传时的不确定感。</text>
      <text class="remark-content">{{ caseInfo.upload_guide }}</text>
    </view>

    <view v-if="caseCapabilities.fields.canViewClientRemark && caseInfo && caseInfo.client_remark" class="card">
      <text class="section-title">当事人补充说明</text>
      <text class="meta">该说明对律师与 AI 分析可见，可结合材料一起判断。</text>
      <text class="remark-content">{{ caseInfo.client_remark }}</text>
    </view>

    <view v-if="caseInfo && caseCapabilities.actions.canEditLawyerRemark" class="card">
      <case-remark-input
        title="律师内部备注"
        hint="仅律师可见，可用于引导后续分析"
        placeholder="记录分析方向、风险点、待补证据或需要复核的问题..."
        submit-label="保存备注"
        :show-voice="false"
        :max-length="5000"
        :show-existing-remark="false"
        :prefill-text="caseInfo.lawyer_remark"
        :clear-on-submit="false"
        :allow-empty-submit="true"
        :submit-handler="handleLawyerRemarkSubmit"
        success-text="备注已保存"
      />
    </view>

    <view
      v-else-if="caseCapabilities.fields.canViewLawyerRemark && caseInfo && caseInfo.lawyer_remark"
      class="card"
    >
      <text class="section-title">律师内部备注</text>
      <text class="meta">当前账号可查看该备注，但不能修改。</text>
      <text class="remark-content">{{ caseInfo.lawyer_remark }}</text>
    </view>

    <view class="section-title">案件时间线</view>
    <view v-if="!timeline.length" class="card file-card">
      <text>当前暂无时间线记录。</text>
    </view>
    <view v-for="(item, index) in timeline" :key="index" class="card file-card">
      <text class="timeline-title">{{ item.title }}</text>
      <text class="meta">{{ item.description }}</text>
      <text class="meta">{{ formatTime(item.occurred_at) }}</text>
    </view>

    <view class="section-title">案件文件</view>
    <view v-if="!files.length" class="card file-card">
      <text>当前还没有文件材料。</text>
    </view>
    <view v-for="file in files" :key="file.id" class="card file-card">
      <text>{{ file.file_name }}</text>
      <text v-if="file.capabilities.fields.canViewDescription" class="meta">说明：{{ file.description }}</text>
      <text class="meta">上传人：{{ file.uploader ? file.uploader.real_name : "未知" }}</text>
      <view class="file-actions">
        <button class="ghost-btn" :disabled="!file.capabilities.actions.canDownload" @click="previewFile(file)">预览</button>
        <button class="ghost-btn" :disabled="!file.capabilities.actions.canDownload" @click="downloadFile(file)">下载</button>
        <button
          v-if="file.capabilities.actions.canDelete"
          class="ghost-btn danger-btn"
          :disabled="deletingFileId === file.id"
          @click="deleteFile(file)"
        >
          删除
        </button>
      </view>
      <text v-if="!file.capabilities.actions.canDownload" class="meta">该文件当前只展示名称，不支持下载。</text>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import CaseRemarkInput from "../../components/CaseRemarkInput.vue";
import LongTaskStatusCard from "../../components/LongTaskStatusCard.vue";
import PageStatusBanner from "../../components/PageStatusBanner.vue";
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { updateLawyerRemark } from "../../features/cases/api";
import { buildCaseLongTaskCard, buildCaseTopFeedbackBanner } from "../../features/cases/feedback";
import { formatText } from "../../shared/lib/display";
import { createLawyerCaseDetailController } from "../../features/cases/detail-controller";
import { casesApi, filesApi } from "../../shared/api/domain-api";
import { downloadCaseFile, previewCaseFile } from "../../shared/lib/file";
import { friendlyError, showFormError } from "../../shared/lib/form";
import { ensureWorkspaceAccess } from "../../features/workspace/workspace";

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
    canGenerateInvite: false,
    canEditLawyerRemark: false,
  }),
  fields: Object.freeze({
    canViewUploadGuide: false,
    canViewClientRemark: false,
    canViewLawyerRemark: false,
  }),
});

export default {
  components: {
    CaseRemarkInput,
    LongTaskStatusCard,
    PageStatusBanner,
    WorkspaceTabBar,
  },
  data() {
    return {
      caseId: 0,
      caseInfo: null,
      caseStage: EMPTY_CASE_STAGE,
      caseCapabilities: EMPTY_CASE_CAPABILITIES,
      currentUser: null,
      files: [],
      invitePath: "",
      inviteLoading: false,
      timeline: [],
      deletingFileId: 0,
    };
  },
  computed: {
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
      });
    },
  },
  async onLoad(options) {
    const user = ensureWorkspaceAccess();
    if (!user) {
      return;
    }
    this.currentUser = user;
    this.caseId = Number(options.id || 0);
    try {
      await this.loadCaseDetail();
    } catch (error) {
      showFormError(friendlyError(error, "加载失败"));
    }
  },
  onUnload() {
    if (this.detailController) {
      this.detailController.dispose();
      this.detailController = null;
    }
  },
  methods: {
    formatText,
    ensureDetailController() {
      if (!this.detailController) {
        this.detailController = createLawyerCaseDetailController();
      }
      return this.detailController;
    },
    applyDetailState(snapshot = {}) {
      const nextSnapshot = snapshot || {};
      this.caseId = Number(nextSnapshot.caseId || this.caseId || 0);
      this.caseInfo = nextSnapshot.caseInfo || null;
      this.caseStage = nextSnapshot.caseStage || EMPTY_CASE_STAGE;
      this.caseCapabilities = nextSnapshot.caseCapabilities || EMPTY_CASE_CAPABILITIES;
      this.timeline = Array.isArray(nextSnapshot.timeline) ? nextSnapshot.timeline : [];
      this.files = Array.isArray(nextSnapshot.files) ? nextSnapshot.files : [];
    },
    async loadCaseDetail() {
      const snapshot = await this.ensureDetailController().load({
        caseId: this.caseId,
        viewer: this.currentUser,
      });
      this.applyDetailState(snapshot);
    },
    async handleLawyerRemarkSubmit(text) {
      if (!this.caseCapabilities.actions.canEditLawyerRemark) {
        throw { message: "当前账号不能修改律师备注" };
      }
      await updateLawyerRemark(this.caseId, text);
      if (this.caseInfo) {
        this.caseInfo = { ...this.caseInfo, lawyer_remark: text };
      }
      return this.caseInfo;
    },
    async loadInvite() {
      if (!this.caseCapabilities.actions.canGenerateInvite) {
        showFormError("当前账号不能生成邀请");
        return;
      }
      if (this.inviteLoading) {
        return;
      }
      this.inviteLoading = true;
      try {
        const result = await casesApi.getCaseInviteQrcode(this.caseId);
        this.invitePath = result.path;
      } catch (error) {
        showFormError(friendlyError(error, "获取邀请失败"));
      } finally {
        this.inviteLoading = false;
      }
    },
    copyInvitePath() {
      if (!this.invitePath) {
        return;
      }
      uni.setClipboardData({
        data: this.invitePath,
        success: () => uni.showToast({ title: "邀请路径已复制", icon: "success" }),
      });
    },
    formatTime(value) {
      if (!value) {
        return "-";
      }
      return String(value).replace("T", " ").slice(0, 19);
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
    async deleteFile(file) {
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
        this.files = this.files.filter((f) => f.id !== file.id);
        uni.showToast({ title: "已删除", icon: "success" });
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
.meta,
.invite-label,
.invite-path {
  display: block;
  margin-top: 12rpx;
}

.invite-tip {
  color: #475569;
  line-height: 1.6;
}

.file-card {
  margin-bottom: 20rpx;
}

.remark-content {
  display: block;
  margin-top: 8rpx;
  color: var(--text-main);
  font-size: 28rpx;
  line-height: 1.7;
  white-space: pre-wrap;
}

.invite-box {
  margin-top: 24rpx;
  padding: 20rpx;
  background: #eff6ff;
  border-radius: 18rpx;
}

.invite-path {
  color: #1d4ed8;
  word-break: break-all;
}

.primary-btn {
  width: 100%;
  height: 84rpx;
  margin-top: 24rpx;
  border-radius: 18rpx;
  background: #2563eb;
  color: #fff;
}

.ghost-btn {
  margin-top: 16rpx;
  background: transparent;
  color: #1d4ed8;
}

.danger-btn {
  color: #dc2626;
}

.file-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 12rpx;
}

.timeline-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
}
</style>


