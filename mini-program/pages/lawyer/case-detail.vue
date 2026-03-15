<template>
  <view class="page-container">
    <view class="card" v-if="caseInfo">
      <text class="section-title">{{ caseInfo.title }}</text>
      <text class="meta">案号：{{ caseInfo.case_number }}</text>
      <text class="meta">状态：{{ caseInfo.status }}</text>
      <text class="meta">当事人：{{ caseInfo.client ? caseInfo.client.real_name : '未关联' }}</text>
      <button class="primary-btn" @click="loadInvite">生成当事人邀请</button>
      <view v-if="invitePath" class="invite-box">
        <text class="invite-label">小程序路径</text>
        <text class="invite-path">{{ invitePath }}</text>
        <button class="ghost-btn" @click="copyInvitePath">复制路径</button>
      </view>
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
      <text class="meta">上传人：{{ file.uploader ? file.uploader.real_name : '未知' }}</text>
      <view class="file-actions">
        <button class="ghost-btn" @click="previewFile(file)">预览</button>
        <button class="ghost-btn" @click="downloadFile(file)">下载</button>
      </view>
    </view>
  </view>
</template>

<script>
import { get } from "../../common/http";
import { downloadCaseFile, previewCaseFile } from "../../common/file";
import { requireLogin } from "../../common/session";
import { friendlyError, showFormError } from "../../common/form";

export default {
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
    if (!requireLogin()) {
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
    async loadCaseDetail() {
      this.caseInfo = await get(`/cases/${this.caseId}`);
      this.timeline = this.caseInfo.timeline || [];
      this.files = await get(`/files/case/${this.caseId}`);
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
        success: () => uni.showToast({ title: "已复制", icon: "success" }),
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

.file-card {
  margin-bottom: 20rpx;
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
