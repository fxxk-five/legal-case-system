<template>
  <view class="page-container fade-in">
    <view class="section-title">文档智能解析</view>

    <view class="glass-card">
      <view class="upload-area" @tap="handleUpload">
        <text class="iconfont icon-upload"></text>
        <text class="upload-text">点击上传案件文档</text>
        <text class="upload-tip">支持 PDF、文档、图片等常见格式</text>
      </view>
    </view>

    <view v-if="currentTask" class="glass-card">
      <view class="task-header">
        <text class="task-title">解析进度（{{ statusText }}）</text>
        <text class="task-percent">{{ currentTask.progress }}%</text>
      </view>
      <view class="progress-bar">
        <view class="progress-inner" :style="{ width: currentTask.progress + '%' }"></view>
      </view>
      <text class="task-msg">{{ displayMessage }}</text>
      <text class="task-conn">{{ wsConnected ? '实时通道已连接' : '实时通道重连中，已启用轮询补偿' }}</text>

      <button v-if="canRetry" class="retry-btn" :loading="retrying" @tap="handleRetry">
        失败重试
      </button>
    </view>

    <view v-if="facts.length > 0" class="facts-section">
      <view class="section-title">提取的事实</view>
      <view v-for="fact in facts" :key="fact.id" class="glass-card fact-item">
        <view class="fact-tag" :class="fact.fact_type">{{ getTypeText(fact.fact_type) }}</view>
        <view class="fact-content">{{ fact.description }}</view>
        <view class="fact-time" v-if="fact.occurrence_time">{{ fact.occurrence_time }}</view>
      </view>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import WorkspaceTabBar from "@/components/WorkspaceTabBar.vue";
import { getCaseFacts, getTaskStatus, parseDocument, retryTask } from "@/common/http.js";
import { createAITaskTracker, getTaskStatusText, normalizeTask } from "@/common/aiTask.js";
import { friendlyError, showFormError } from "@/common/form";
import { redirectByRole } from "@/common/session";
import { ensureWorkspaceAccess } from "@/common/workspace";

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      caseId: null,
      facts: [],
      currentTask: null,
      retrying: false,
      wsConnected: false,
      tracker: null,
    };
  },
  computed: {
    statusText() {
      return getTaskStatusText(this.currentTask?.status);
    },
    displayMessage() {
      if (!this.currentTask) {
        return "";
      }
      return this.currentTask.message || this.statusText;
    },
    canRetry() {
      return this.currentTask && this.currentTask.status === "failed";
    },
  },
  onLoad(options) {
    const user = ensureWorkspaceAccess();
    if (!user) {
      return;
    }

    this.caseId = Number(options.id || options.caseId || 0);
    if (!this.caseId) {
      showFormError("缺少案件参数");
      redirectByRole(user);
      return;
    }
    this.loadFacts();
  },
  onUnload() {
    this.stopTracker();
  },
  methods: {
    async loadFacts() {
      try {
        const res = await getCaseFacts(this.caseId);
        this.facts = res.items || [];
      } catch (error) {
        showFormError(friendlyError(error, "加载事实数据失败"));
      }
    },
    handleUpload() {
      uni.chooseMessageFile({
        count: 1,
        type: "file",
        success: (res) => {
          const file = res.tempFiles && res.tempFiles.length ? res.tempFiles[0] : null;
          if (!file) {
            showFormError("未选择文件");
            return;
          }
          this.startParse(file);
        },
      });
    },
    async startParse(file) {
      uni.showLoading({ title: "上传并启动解析中..." });
      try {
        const task = await parseDocument(this.caseId, file);
        this.applyTask(task);
        uni.showToast({ title: "解析任务已启动", icon: "success" });
      } catch (error) {
        showFormError(friendlyError(error, "启动解析任务失败"));
      } finally {
        uni.hideLoading();
      }
    },
    async handleRetry() {
      if (!this.currentTask || this.retrying) {
        return;
      }

      this.retrying = true;
      try {
        const nextTask = await retryTask(this.currentTask.task_id, "manual_retry_from_mini");
        this.applyTask(nextTask);
        uni.showToast({ title: "已提交重试", icon: "success" });
      } catch (error) {
        showFormError(friendlyError(error, "提交重试失败"));
      } finally {
        this.retrying = false;
      }
    },
    applyTask(task) {
      this.currentTask = normalizeTask(task);
      this.startTracker(this.currentTask);
    },
    startTracker(task) {
      this.stopTracker();

      this.tracker = createAITaskTracker({
        getTaskStatus,
        onUpdate: (nextTask, meta) => {
          this.currentTask = normalizeTask(nextTask);
          this.wsConnected = Boolean(meta && meta.connected);
        },
        onCompleted: async () => {
          uni.showToast({ title: "解析任务已完成", icon: "success" });
          await this.loadFacts();
        },
        onFailed: (failedTask) => {
          this.currentTask = normalizeTask(failedTask);
          showFormError(this.currentTask.message || "解析任务失败");
        },
        onError: (error) => {
          console.error("AI task tracking failed:", error);
        },
      });

      this.tracker.start(task);
    },
    stopTracker() {
      if (this.tracker) {
        this.tracker.stop();
        this.tracker = null;
      }
      this.wsConnected = false;
    },
    getTypeText(type) {
      const texts = {
        party: "当事人",
        timeline: "时间线",
        evidence: "证据",
        law_reference: "法律条款",
      };
      return texts[type] || type;
    },
  },
};
</script>

<style lang="scss" scoped>
.upload-area {
  height: 300rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 2rpx dashed #dcdfe6;
  border-radius: var(--radius-md);

  .icon-upload {
    font-size: 80rpx;
    color: var(--accent-color);
    margin-bottom: 20rpx;
  }

  .upload-text {
    font-size: 30rpx;
    font-weight: 600;
    color: var(--primary-color);
  }

  .upload-tip {
    font-size: 24rpx;
    color: var(--text-sub);
    margin-top: 12rpx;
  }
}

.task-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20rpx;

  .task-title {
    font-weight: 600;
  }

  .task-percent {
    color: var(--accent-color);
    font-weight: 700;
  }
}

.progress-bar {
  height: 12rpx;
  background: #f0f2f5;
  border-radius: 6rpx;
  overflow: hidden;
  margin-bottom: 16rpx;

  .progress-inner {
    height: 100%;
    background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
    transition: width 0.3s ease;
  }
}

.task-msg {
  display: block;
  font-size: 24rpx;
  color: var(--text-sub);
}

.task-conn {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #64748b;
}

.retry-btn {
  margin-top: 20rpx;
  width: 100%;
  height: 78rpx;
  border-radius: 14rpx;
  background: #fee2e2;
  color: #be123c;
  font-size: 26rpx;
  font-weight: 600;
}

.fact-item {
  position: relative;
  padding-top: 60rpx;

  .fact-tag {
    position: absolute;
    top: 24rpx;
    left: 32rpx;
    font-size: 20rpx;
    padding: 4rpx 16rpx;
    border-radius: 20rpx;
    background: #f0f2f5;
    color: var(--text-sub);

    &.party {
      background: #e1f5fe;
      color: #039be5;
    }

    &.timeline {
      background: #fff8e1;
      color: #ffb300;
    }

    &.evidence {
      background: #e8f5e9;
      color: #43a047;
    }

    &.law_reference {
      background: #ffebee;
      color: #e53935;
    }
  }

  .fact-content {
    font-size: 28rpx;
    line-height: 1.6;
  }

  .fact-time {
    margin-top: 16rpx;
    font-size: 22rpx;
    color: var(--text-sub);
    text-align: right;
  }
}
</style>
