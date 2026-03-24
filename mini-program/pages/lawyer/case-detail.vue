<template>
  <view class="page-container workspace-page">
    <view class="card" v-if="caseInfo">
      <text class="section-title">{{ caseInfo.title }}</text>
      <text class="meta">案号：{{ caseInfo.case_number }}</text>
      <text class="meta">状态：{{ formatCaseStatus(caseInfo.status) }}</text>
      <text class="meta">当事人：{{ formatText(caseInfo.client ? caseInfo.client.real_name : "", "未关联") }}</text>
      <button class="primary-btn" @click="loadInvite">生成当事人邀请</button>
      <view v-if="invitePath" class="invite-box">
        <text class="invite-label">邀请路径</text>
        <text class="meta invite-tip">把这条路径发给当事人，对方进入小程序后可直接绑定到当前案件。</text>
        <text class="invite-path">{{ invitePath }}</text>
        <button class="ghost-btn" @click="copyInvitePath">复制路径</button>
      </view>
    </view>

    <view v-if="caseInfo && caseInfo.client_remark" class="card">
      <text class="section-title">当事人补充说明</text>
      <text class="meta">该说明对律师与 AI 分析可见，可结合材料一起判断。</text>
      <text class="remark-content">{{ caseInfo.client_remark }}</text>
    </view>

    <view v-if="caseInfo" class="card">
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
      <text class="meta">上传人：{{ file.uploader ? file.uploader.real_name : "未知" }}</text>
      <view class="file-actions">
        <button class="ghost-btn" @click="previewFile(file)">预览</button>
        <button class="ghost-btn" @click="downloadFile(file)">下载</button>
      </view>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import CaseRemarkInput from "../../components/CaseRemarkInput.vue";
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { getCaseDetail, getRemarkValue, updateLawyerRemark } from "../../common/cases";
import { formatCaseStatus, formatText } from "../../common/display";
import { get } from "../../common/http";
import { downloadCaseFile, previewCaseFile } from "../../common/file";
import { friendlyError, showFormError } from "../../common/form";
import { ensureWorkspaceAccess } from "../../common/workspace";

export default {
  components: {
    CaseRemarkInput,
    WorkspaceTabBar,
  },
  data() {
    return {
      caseId: 0,
      caseInfo: null,
      files: [],
      invitePath: "",
      timeline: [],
    };
  },
  async onLoad(options) {
    const user = ensureWorkspaceAccess();
    if (!user) {
      return;
    }
    this.caseId = Number(options.id || 0);
    try {
      await this.loadCaseDetail();
    } catch (error) {
      showFormError(friendlyError(error, "加载失败"));
    }
  },
  methods: {
    formatCaseStatus,
    formatText,
    async loadCaseDetail() {
      const detail = await getCaseDetail(this.caseId);
      this.caseInfo = {
        lawyer_remark: "",
        client_remark: "",
        ...(detail || {}),
      };
      this.timeline = this.caseInfo.timeline || [];
      this.files = await get(`/files/case/${this.caseId}`);
    },
    async handleLawyerRemarkSubmit(text) {
      const detail = await updateLawyerRemark(this.caseId, text);
      this.caseInfo = {
        ...(this.caseInfo || {}),
        ...(detail || {}),
        lawyer_remark: getRemarkValue(detail, "lawyer_remark", text),
      };
      return detail;
    },
    async loadInvite() {
      try {
        const result = await get(`/cases/${this.caseId}/invite-qrcode`);
        this.invitePath = result.path;
      } catch (error) {
        showFormError(friendlyError(error, "获取邀请失败"));
      }
    },
    copyInvitePath() {
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
      try {
        await previewCaseFile(file);
      } catch (error) {
        showFormError(friendlyError(error, "文件预览失败"));
      }
    },
    async downloadFile(file) {
      try {
        await downloadCaseFile(file);
      } catch (error) {
        showFormError(friendlyError(error, "文件下载失败"));
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
