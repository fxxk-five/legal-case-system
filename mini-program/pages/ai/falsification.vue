<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">证伪校验</text>
      <text class="page-hero-desc">查看案件证伪校验入口、任务进度与最近校验结果。</text>
    </view>

    <view v-if="entryBlocked" class="glass-card notice-card">
      <view class="notice-title">当前入口暂未开放</view>
      <view class="notice-desc">
        为避免误触发受限的智能分析能力，小程序端暂不开放发起证伪校验。你可以通过底栏返回案件管理或“我的”。
      </view>
    </view>

    <view class="glass-card intro-card">
      <view class="intro-title">启动证伪校验</view>
      <view class="intro-desc">
        系统会针对案件事实做一致性检查，识别可疑陈述、证据缺口与高风险点。
      </view>
      <button class="btn-primary danger" :disabled="entryBlocked" :loading="loading" @tap="handleStartFalsification">
        开始校验
      </button>
    </view>

    <view v-if="currentTask" class="glass-card">
      <view class="task-header">
        <text class="task-title">校验进度（{{ statusText }}）</text>
        <text class="task-percent">{{ currentTask.progress }}%</text>
      </view>
      <view class="progress-bar">
        <view class="progress-inner" :style="{ width: currentTask.progress + '%' }"></view>
      </view>
      <text class="task-msg">{{ displayMessage }}</text>
      <text class="task-conn">{{ wsConnected ? "实时通道已连接" : "实时通道重连中，已启用轮询补偿" }}</text>

      <button v-if="canRetry" class="retry-btn" :loading="retrying" @tap="handleRetry">失败重试</button>
    </view>

    <view v-if="falsificationRecords.length > 0" class="results-section">
      <view class="summary-grid">
        <view class="summary-item">
          <text class="label">总校验项</text>
          <text class="value">{{ falsificationSummary.total }}</text>
        </view>
        <view class="summary-item danger">
          <text class="label">疑似问题</text>
          <text class="value">{{ falsificationSummary.falsified }}</text>
        </view>
        <view class="summary-item warning">
          <text class="label">高风险</text>
          <text class="value">{{ falsificationSummary.critical }}</text>
        </view>
      </view>

      <view v-for="record in falsificationRecords" :key="record.id" class="glass-card record-card">
        <view class="record-header">
          <view class="tag" :class="record.is_falsified ? 'danger' : 'success'">
            {{ record.is_falsified ? "疑似问题" : "校验通过" }}
          </view>
          <view class="tag severity" :class="record.severity">
            {{ getSeverityText(record.severity) }}
          </view>
          <text class="time">{{ record.created_at }}</text>
        </view>

        <view class="record-body">
          <view class="record-block">
            <text class="label">校验事实</text>
            <text class="content">{{ record.fact_description || "-" }}</text>
          </view>
          <view v-if="record.reason" class="record-block falsification-reason">
            <text class="label">问题说明</text>
            <text class="content">{{ record.reason }}</text>
          </view>
          <view v-if="record.evidence_gap" class="record-block evidence-gap">
            <text class="label">证据缺口</text>
            <text class="content">{{ record.evidence_gap }}</text>
          </view>
        </view>
      </view>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import WorkspaceTabBar from "@/components/WorkspaceTabBar.vue";
import { createAITaskTracker, getTaskStatusText, normalizeTask } from "@/common/aiTask.js";
import { friendlyError, showFormError } from "@/common/form";
import { getAnalysisResults, getFalsificationResults, getTaskStatus, retryTask, startFalsification } from "@/common/http.js";
import { redirectByRole } from "@/common/session";
import { ensureWorkspaceAccess } from "@/common/workspace";

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      caseId: null,
      falsificationRecords: [],
      currentTask: null,
      entryBlocked: true,
      loading: false,
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
    falsificationSummary() {
      const total = this.falsificationRecords.length;
      const falsified = this.falsificationRecords.filter((item) => item.is_falsified).length;
      const critical = this.falsificationRecords.filter((item) => item.severity === "critical").length;
      return { total, falsified, critical };
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
    }
  },
  onUnload() {
    this.stopTracker();
  },
  methods: {
    async loadResults() {
      try {
        const res = await getFalsificationResults(this.caseId);
        this.falsificationRecords = res.items || [];
      } catch (error) {
        showFormError(friendlyError(error, "加载证伪结果失败"));
      }
    },
    async handleStartFalsification() {
      if (this.entryBlocked) {
        showFormError("当前小程序暂未开放证伪校验发起入口");
        return;
      }

      this.loading = true;
      try {
        const analysisRes = await getAnalysisResults(this.caseId);
        const analysisId = (analysisRes.items || [])[0]?.id;
        if (!analysisId) {
          showFormError("请先完成法律分析");
          return;
        }

        const task = await startFalsification(this.caseId, analysisId);
        this.applyTask(task);
        uni.showToast({ title: "证伪任务已启动", icon: "success" });
      } catch (error) {
        showFormError(friendlyError(error, "启动证伪失败"));
      } finally {
        this.loading = false;
      }
    },
    async handleRetry() {
      if (this.entryBlocked) {
        showFormError("当前小程序暂未开放证伪校验发起入口");
        return;
      }
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
          uni.showToast({ title: "证伪任务已完成", icon: "success" });
          await this.loadResults();
        },
        onFailed: (failedTask) => {
          this.currentTask = normalizeTask(failedTask);
          showFormError(this.currentTask.message || "证伪任务失败");
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
    getSeverityText(severity) {
      const texts = {
        critical: "高风险",
        major: "中风险",
        minor: "低风险",
      };
      return texts[severity] || severity || "未设置";
    },
  },
};
</script>

<style lang="scss" scoped>
.notice-card {
  margin-bottom: 24rpx;
}

.notice-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 12rpx;
}

.notice-desc {
  font-size: 24rpx;
  line-height: 1.7;
  color: var(--text-sub);
}

.intro-card {
  text-align: center;
  padding: 60rpx 40rpx;
}

.intro-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #f56c6c;
  margin-bottom: 20rpx;
}

.intro-desc {
  font-size: 26rpx;
  color: var(--text-sub);
  margin-bottom: 40rpx;
  line-height: 1.6;
}

.btn-primary.danger {
  background: #f56c6c;
}

.summary-grid {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 32rpx;
}

.summary-item {
  flex: 1;
  background: #ffffff;
  padding: 24rpx;
  border-radius: 24rpx;
  text-align: center;
  box-shadow: var(--shadow-soft);
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.summary-item .label {
  font-size: 22rpx;
  color: var(--text-sub);
}

.summary-item .value {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--primary-color);
}

.summary-item.danger {
  border-bottom: 6rpx solid #f56c6c;
}

.summary-item.danger .value {
  color: #f56c6c;
}

.summary-item.warning {
  border-bottom: 6rpx solid #e6a23c;
}

.summary-item.warning .value {
  color: #e6a23c;
}

.record-card {
  padding: 32rpx;
}

.record-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.tag {
  font-size: 20rpx;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
}

.tag.success {
  background: #e8f5e9;
  color: #43a047;
}

.tag.danger {
  background: #ffebee;
  color: #e53935;
}

.tag.severity.critical {
  background: #1a1c1e;
  color: #ffffff;
}

.tag.severity.major {
  background: #fef3c7;
  color: #92400e;
}

.tag.severity.minor {
  background: #f0f2f5;
  color: var(--text-sub);
}

.time {
  margin-left: auto;
  font-size: 22rpx;
  color: var(--text-sub);
}

.record-body {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.record-block {
  padding: 20rpx;
  border-radius: 16rpx;
  background: #f8fafc;
}

.record-block .label {
  display: block;
  margin-bottom: 8rpx;
  font-weight: 700;
  font-size: 26rpx;
  color: var(--primary-color);
}

.record-block .content {
  font-size: 26rpx;
  line-height: 1.6;
  color: var(--text-main);
}

.falsification-reason {
  background: rgba(245, 108, 108, 0.05);
}

.falsification-reason .label {
  color: #f56c6c;
}

.evidence-gap {
  background: rgba(230, 162, 60, 0.05);
}

.evidence-gap .label {
  color: #e6a23c;
}

.task-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.task-title {
  font-weight: 600;
}

.task-percent {
  color: var(--accent-color);
  font-weight: 700;
}

.progress-bar {
  height: 12rpx;
  background: #f0f2f5;
  border-radius: 6rpx;
  overflow: hidden;
  margin-bottom: 16rpx;
}

.progress-inner {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
  transition: width 0.3s ease;
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
</style>
