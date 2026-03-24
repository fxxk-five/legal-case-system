<template>
  <view class="page-container fade-in">
    <view class="card page-hero">
      <text class="page-hero-title">补充材料</text>
      <text class="page-hero-desc">
        按证据项逐个补充材料，系统会自动触发重新解析，并以 5 分钟窗口做防抖处理。上传成功后，律师端与当事人端会同步更新进度。
      </text>
    </view>

    <view class="card">
      <text class="section-title">案件信息</text>
      <text class="meta">案件：{{ caseTitle }}</text>
      <text class="meta">已选择 {{ selectedFiles.length }} 个文件，支持聊天/本地文件与相册图片。</text>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-primary action-button" :disabled="submitting" @click="chooseFiles">添加证据</button>
        <button class="toolbar-button toolbar-button-secondary action-button" @click="backToDetail">返回案件详情</button>
      </view>
    </view>

    <view v-if="!selectedFiles.length" class="card empty-state">尚未选择文件，点击“添加证据”开始上传。</view>

    <view v-for="(item, index) in selectedFiles" :key="item.uid" class="card file-card">
      <view class="row-between row-top">
        <view class="file-meta">
          <text class="list-card-title">{{ item.name }}</text>
          <text class="meta">来源：{{ item.sourceText }}</text>
        </view>
        <text class="tag" :class="item.statusTagClass">{{ item.statusText }}</text>
      </view>
      <input
        v-model="item.description"
        class="input field-gap"
        maxlength="200"
        placeholder="可选：补充说明（最多 200 字）"
      />
      <text v-if="item.error" class="error-text">{{ item.error }}</text>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-secondary action-button" :disabled="submitting" @click="removeFile(index)">移除</button>
      </view>
    </view>

    <view class="card">
      <text class="section-title">关键证据提示</text>
      <text class="meta">- 借贷类：借条、转账记录、催收记录</text>
      <text class="meta">- 劳动类：劳动合同、工资流水、考勤记录</text>
      <text class="meta">- 合同类：合同原件、履约凭证、沟通记录</text>
    </view>

    <view class="footer-bar">
      <button class="toolbar-button toolbar-button-primary submit-button" :disabled="!selectedFiles.length || submitting" :loading="submitting" @click="submitAll">
        上传完成，开始分析
      </button>
    </view>

    <client-tab-bar current-key="cases" />
  </view>
</template>

<script>
import ClientTabBar from "../../components/ClientTabBar.vue";
import { get, upload } from "../../common/http";
import { friendlyError, showFormError } from "../../common/form";
import { buildClientCaseDetailUrl } from "../../common/role-routing";
import { ensureClientAccess, redirectByRole } from "../../common/session";

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

function buildFileItem(file, index, sourceText) {
  const rawName = file.name || file.path || `file-${index + 1}`;
  const name = String(rawName).split(/[\\/]/).pop();
  return {
    uid: `${Date.now()}-${index}-${Math.random().toString(16).slice(2)}`,
    name,
    path: file.path || file.tempFilePath || "",
    sourceText,
    status: "waiting",
    statusText: STATUS_TEXT_MAP.waiting,
    statusTagClass: STATUS_TAG_CLASS_MAP.waiting,
    description: "",
    error: "",
  };
}

export default {
  components: {
    ClientTabBar,
  },
  data() {
    return {
      caseId: 0,
      caseTitle: "-",
      submitting: false,
      selectedFiles: [],
    };
  },
  onLoad(options) {
    const user = ensureClientAccess();
    if (!user) {
      return;
    }

    const caseId = Number(options.caseId || 0);
    if (!caseId) {
      showFormError("缺少案件参数");
      redirectByRole(user);
      return;
    }
    this.caseId = caseId;
    this.loadCase();
  },
  methods: {
    async loadCase() {
      try {
        const detail = await get(`/cases/${this.caseId}`);
        this.caseTitle = detail?.title || `案件 #${this.caseId}`;
      } catch (error) {
        showFormError(friendlyError(error, "获取案件信息失败"));
      }
    },
    appendFiles(files, sourceText) {
      if (!Array.isArray(files) || !files.length) {
        return;
      }
      const nextItems = files
        .map((file, index) => buildFileItem(file, index, sourceText))
        .filter((item) => item.path);
      if (!nextItems.length) {
        showFormError("未识别到可上传的文件");
        return;
      }
      this.selectedFiles = [...this.selectedFiles, ...nextItems];
    },
    chooseMessageFiles() {
      uni.chooseMessageFile({
        count: 20,
        type: "all",
        success: ({ tempFiles = [] }) => {
          this.appendFiles(tempFiles, "聊天/本地文件");
        },
        fail: (error) => {
          showFormError(friendlyError(error, "选择文件失败"));
        },
      });
    },
    chooseAlbumImages() {
      uni.chooseImage({
        count: 9,
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
    chooseFiles() {
      uni.showActionSheet({
        itemList: ["聊天/本地文件", "相册图片"],
        success: ({ tapIndex }) => {
          if (tapIndex === 0) {
            this.chooseMessageFiles();
            return;
          }
          this.chooseAlbumImages();
        },
      });
    },
    backToDetail() {
      uni.redirectTo({ url: buildClientCaseDetailUrl(this.caseId) });
    },
    removeFile(index) {
      this.selectedFiles.splice(index, 1);
    },
    patchFileStatus(index, status, error = "") {
      const nextStatus = String(status || "waiting").toLowerCase();
      const target = this.selectedFiles[index];
      if (!target) {
        return;
      }
      target.status = nextStatus;
      target.statusText = STATUS_TEXT_MAP[nextStatus] || "处理中";
      target.statusTagClass = STATUS_TAG_CLASS_MAP[nextStatus] || "tag-neutral";
      target.error = error;
    },
    async submitAll() {
      if (!this.selectedFiles.length || this.submitting) {
        return;
      }

      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "确认提交",
          content: "提交后将自动触发重新解析，是否继续？",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
      if (!confirmed) {
        return;
      }

      this.submitting = true;
      let successCount = 0;
      let failedCount = 0;

      for (let i = 0; i < this.selectedFiles.length; i += 1) {
        const item = this.selectedFiles[i];
        if (!item.path) {
          failedCount += 1;
          this.patchFileStatus(i, "failed", "文件路径无效");
          continue;
        }

        this.patchFileStatus(i, "uploading", "");
        try {
          const desc = (item.description || "").trim();
          const query = desc ? `?description=${encodeURIComponent(desc)}` : "";
          await upload(`/cases/${this.caseId}/files${query}`, item.path, "upload");
          successCount += 1;
          this.patchFileStatus(i, "success", "");
        } catch (error) {
          failedCount += 1;
          this.patchFileStatus(i, "failed", friendlyError(error, "上传失败"));
        }
      }

      this.submitting = false;
      if (successCount <= 0) {
        showFormError("没有文件上传成功，请检查后重试");
        return;
      }

      if (failedCount > 0) {
        this.selectedFiles = this.selectedFiles.filter((item) => item.status !== "success");
        showFormError(`已成功上传 ${successCount} 个文件，仍有 ${failedCount} 个失败，请处理后重试`);
        return;
      }

      uni.showToast({
        title: `已上传 ${successCount} 个文件`,
        icon: "success",
      });

      setTimeout(() => {
        uni.redirectTo({ url: buildClientCaseDetailUrl(this.caseId) });
      }, 300);
    },
  },
};
</script>

<style scoped>
.card-toolbar,
.field-gap {
  margin-top: 18rpx;
}

.action-button,
.submit-button {
  width: 100%;
}

.sms-button {
  width: 240rpx;
}

.file-card {
  margin-bottom: 20rpx;
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

.file-meta {
  flex: 1;
}

.error-text {
  display: block;
  margin-top: 8rpx;
  color: #b91c1c;
  font-size: 24rpx;
}

.footer-bar {
  position: sticky;
  bottom: 0;
  padding-top: 12rpx;
  padding-bottom: env(safe-area-inset-bottom);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0), #f8fafc 30%);
}
</style>
