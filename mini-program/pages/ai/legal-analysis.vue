<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">法律分析</text>
      <text class="page-hero-desc">查看案件法律分析入口、任务进度与最新分析结果。</text>
    </view>

    <view v-if="entryBlocked" class="glass-card notice-card">
      <view class="notice-title">当前入口暂未开放</view>
      <view class="notice-desc">
        为避免误触发受限的智能分析能力，小程序端暂不开放发起法律分析。你可以通过底栏返回案件管理或“我的”。
      </view>
    </view>

    <view class="glass-card intro-card">
      <view class="intro-title">启动智能法律分析</view>
      <view class="intro-desc">
        基于已提取的案件事实，系统会生成胜诉率预估、强弱项分析和后续行动建议。
      </view>
      <button class="btn-primary" :disabled="entryBlocked" :loading="loading" @tap="handleStartAnalysis">
        开始分析
      </button>
    </view>

    <view v-if="currentTask" class="glass-card">
      <view class="task-header">
        <text class="task-title">分析进度（{{ statusText }}）</text>
        <text class="task-percent">{{ currentTask.progress }}%</text>
      </view>
      <view class="progress-bar">
        <view class="progress-inner" :style="{ width: currentTask.progress + '%' }"></view>
      </view>
      <text class="task-msg">{{ displayMessage }}</text>
      <text class="task-conn">{{ wsConnected ? "实时通道已连接" : "实时通道重连中，已启用轮询补偿" }}</text>

      <button v-if="canRetry" class="retry-btn" :loading="retrying" @tap="handleRetry">失败重试</button>
    </view>

    <view v-if="latestAnalysis" class="results-section">
      <view class="glass-card win-rate-card">
        <view class="win-rate-title">胜诉率预估</view>
        <view class="win-rate-value">{{ (latestAnalysis.win_rate * 100).toFixed(0) }}%</view>
        <view class="win-rate-bar">
          <view class="win-rate-inner" :style="{ width: latestAnalysis.win_rate * 100 + '%' }"></view>
        </view>
      </view>

      <view class="glass-card summary-card">
        <view class="card-title">分析摘要</view>
        <view class="summary-content">{{ latestAnalysis.summary || "暂无摘要" }}</view>
      </view>

      <view class="glass-card swot-card">
        <view class="card-title">强弱项分析</view>
        <view class="swot-grid">
          <view class="swot-item strength">
            <view class="swot-label">优势</view>
            <view v-for="(item, index) in strengths" :key="`s-${index}`" class="swot-text">• {{ item }}</view>
            <view v-if="!strengths.length" class="swot-empty">暂无优势结论</view>
          </view>
          <view class="swot-item weakness">
            <view class="swot-label">风险</view>
            <view v-for="(item, index) in weaknesses" :key="`w-${index}`" class="swot-text">• {{ item }}</view>
            <view v-if="!weaknesses.length" class="swot-empty">暂无风险结论</view>
          </view>
        </view>
      </view>

      <view class="glass-card advice-card">
        <view class="card-title">行动建议</view>
        <view v-for="(item, index) in recommendations" :key="`r-${index}`" class="advice-item">
          <text class="advice-icon">•</text>
          <text class="advice-text">{{ item }}</text>
        </view>
        <view v-if="!recommendations.length" class="swot-empty">暂无行动建议</view>
      </view>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import WorkspaceTabBar from "@/components/WorkspaceTabBar.vue";
import { createAITaskTracker, getTaskStatusText, normalizeTask } from "@/common/aiTask.js";
import { friendlyError, showFormError } from "@/common/form";
import { getAnalysisResults, getTaskStatus, retryTask, startAnalysis } from "@/common/http.js";
import { redirectByRole } from "@/common/session";
import { ensureWorkspaceAccess } from "@/common/workspace";

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      caseId: null,
      latestAnalysis: null,
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
    strengths() {
      return Array.isArray(this.latestAnalysis?.strengths) ? this.latestAnalysis.strengths : [];
    },
    weaknesses() {
      return Array.isArray(this.latestAnalysis?.weaknesses) ? this.latestAnalysis.weaknesses : [];
    },
    recommendations() {
      return Array.isArray(this.latestAnalysis?.recommendations) ? this.latestAnalysis.recommendations : [];
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
    async loadAnalysis() {
      try {
        const res = await getAnalysisResults(this.caseId);
        this.latestAnalysis = (res.items || [])[0] || null;
      } catch (error) {
        showFormError(friendlyError(error, "加载分析结果失败"));
      }
    },
    async handleStartAnalysis() {
      if (this.entryBlocked) {
        showFormError("当前小程序暂未开放法律分析发起入口");
        return;
      }

      this.loading = true;
      try {
        const task = await startAnalysis(this.caseId);
        this.applyTask(task);
        uni.showToast({ title: "分析任务已启动", icon: "success" });
      } catch (error) {
        showFormError(friendlyError(error, "启动分析失败"));
      } finally {
        this.loading = false;
      }
    },
    async handleRetry() {
      if (this.entryBlocked) {
        showFormError("当前小程序暂未开放法律分析发起入口");
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
          uni.showToast({ title: "分析任务已完成", icon: "success" });
          await this.loadAnalysis();
        },
        onFailed: (failedTask) => {
          this.currentTask = normalizeTask(failedTask);
          showFormError(this.currentTask.message || "分析任务失败");
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

  .intro-title {
    font-size: 36rpx;
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 20rpx;
  }

  .intro-desc {
    font-size: 26rpx;
    color: var(--text-sub);
    margin-bottom: 40rpx;
    line-height: 1.6;
  }
}

.win-rate-card {
  text-align: center;

  .win-rate-title {
    font-size: 28rpx;
    color: var(--text-sub);
    margin-bottom: 16rpx;
  }

  .win-rate-value {
    font-size: 72rpx;
    font-weight: 800;
    color: var(--primary-color);
    margin-bottom: 24rpx;
  }

  .win-rate-bar {
    height: 16rpx;
    background: #f0f2f5;
    border-radius: 8rpx;
    overflow: hidden;

    .win-rate-inner {
      height: 100%;
      background: linear-gradient(90deg, #f56c6c, #67c23a);
      transition: width 1s ease-out;
    }
  }
}

.card-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 24rpx;
  border-bottom: 1rpx solid #f0f2f5;
  padding-bottom: 16rpx;
}

.summary-content {
  font-size: 28rpx;
  line-height: 1.8;
  color: var(--text-main);
}

.swot-grid {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.swot-item {
  padding: 24rpx;
  border-radius: var(--radius-md);
}

.swot-label {
  font-size: 26rpx;
  font-weight: 700;
  margin-bottom: 12rpx;
}

.swot-text,
.swot-empty {
  font-size: 24rpx;
  line-height: 1.6;
  margin-bottom: 8rpx;
}

.swot-empty {
  color: var(--text-sub);
}

.strength {
  background: rgba(103, 194, 58, 0.08);
  color: #67c23a;

  .swot-text {
    color: #303133;
  }
}

.weakness {
  background: rgba(245, 108, 108, 0.08);
  color: #f56c6c;

  .swot-text {
    color: #303133;
  }
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  margin-bottom: 20rpx;
  padding: 20rpx;
  background: #f8f9fb;
  border-radius: 16rpx;
}

.advice-icon {
  font-size: 32rpx;
  color: var(--primary-color);
}

.advice-text {
  flex: 1;
  font-size: 26rpx;
  line-height: 1.6;
  color: var(--text-main);
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
