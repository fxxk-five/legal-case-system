<template>
  <view class="page-container">
    <view v-if="caseInfo" class="card">
      <text class="section-title">{{ caseInfo.title }}</text>
      <text class="meta">案号：{{ caseInfo.case_number }}</text>
      <text class="meta">当前状态：{{ caseInfo.status }}</text>
      <text class="meta">负责律师：{{ caseInfo.assigned_lawyer ? caseInfo.assigned_lawyer.real_name : '未指派' }}</text>
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

    <view class="section-title">材料列表</view>
    <view class="card upload-card">
      <button class="primary-btn" :loading="uploading" @click="handleUpload">上传材料</button>
    </view>
    <view v-if="!caseInfo" class="card file-card">
      <text>当前没有可查看的案件，请先通过邀请进入案件。</text>
    </view>
    <view v-else-if="!files.length" class="card file-card">
      <text>当前还没有材料，可先上传一份文件进行演示。</text>
    </view>
    <view v-for="file in files" :key="file.id" class="card file-card">
      <text>{{ file.file_name }}</text>
      <text class="meta">上传时间：{{ file.created_at }}</text>
      <view class="file-actions">
        <button class="ghost-btn" @click="previewFile(file)">预览</button>
        <button class="ghost-btn" @click="downloadFile(file)">下载</button>
      </view>
    </view>
  </view>
</template>

<script>
import { get, uploadByPolicy } from "../../common/http";
import { downloadCaseFile, previewCaseFile } from "../../common/file";
import { requireLogin } from "../../common/session";
import { friendlyError, showFormError } from "../../common/form";

export default {
  data() {
    return {
      caseInfo: null,
      files: [],
      uploading: false,
      timeline: [],
    };
  },
  async onShow() {
    if (!requireLogin()) {
      return;
    }
    try {
      await this.loadData();
    } catch (error) {
      showFormError(friendlyError(error, "获取案件失败"));
    }
  },
  methods: {
    async loadData() {
      const caseList = await get("/cases");
      if (!caseList.length) {
        this.caseInfo = null;
        this.files = [];
        return;
      }
      this.caseInfo = await get(`/cases/${caseList[0].id}`);
      this.timeline = this.caseInfo.timeline || [];
      this.files = await get(`/files/case/${caseList[0].id}`);
    },
    handleUpload() {
      if (!this.caseInfo) {
        uni.showToast({ title: "当前没有可上传的案件", icon: "none" });
        return;
      }

      uni.chooseMessageFile({
        count: 1,
        type: "file",
        success: async ({ tempFiles }) => {
          const target = tempFiles && tempFiles.length ? tempFiles[0] : null;
          if (!target || !target.path) {
            uni.showToast({ title: "未选择文件", icon: "none" });
            return;
          }

          this.uploading = true;
          try {
            const policy = await get(
              `/files/upload-policy?case_id=${this.caseInfo.id}&file_name=${encodeURIComponent(target.name || "upload-file")}&content_type=${encodeURIComponent(target.type || "application/octet-stream")}`
            );
            await uploadByPolicy(policy, target.path);
            uni.showToast({ title: "上传成功", icon: "success" });
            await this.loadData();
          } catch (error) {
            showFormError(friendlyError(error, "上传失败"));
          } finally {
            this.uploading = false;
          }
        },
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
.meta {
  display: block;
  margin-top: 12rpx;
}

.file-card {
  margin-bottom: 20rpx;
}

.upload-card {
  margin-bottom: 20rpx;
}

.primary-btn {
  width: 100%;
  height: 88rpx;
  border-radius: 18rpx;
  background: #0f766e;
  color: #fff;
}

.timeline-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
}

.file-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 12rpx;
}

.ghost-btn {
  background: transparent;
  color: #1d4ed8;
}
</style>
