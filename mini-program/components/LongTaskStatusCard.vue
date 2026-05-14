<template>
  <view class="task-card" :class="toneClass">
    <view class="task-head">
      <view class="task-main">
        <text class="task-title">{{ title }}</text>
        <text class="task-status">{{ statusText }}</text>
      </view>
      <button
        v-if="actionLabel"
        class="task-action"
        :disabled="actionDisabled"
        :loading="actionLoading"
        @click="$emit('action')"
      >
        {{ actionLabel }}
      </button>
    </view>

    <view class="task-progress-track">
      <view class="task-progress-fill" :style="progressStyle"></view>
    </view>
    <text class="task-progress-text">{{ progressText || `当前进度 ${clampedProgress}%` }}</text>

    <text v-if="message" class="task-message">{{ message }}</text>
    <text v-if="hint" class="task-hint">{{ hint }}</text>
  </view>
</template>

<script>
export default {
  name: "LongTaskStatusCard",
  props: {
    tone: {
      type: String,
      default: "info",
    },
    title: {
      type: String,
      default: "任务状态",
    },
    statusText: {
      type: String,
      default: "",
    },
    progress: {
      type: Number,
      default: 0,
    },
    progressText: {
      type: String,
      default: "",
    },
    message: {
      type: String,
      default: "",
    },
    hint: {
      type: String,
      default: "",
    },
    actionLabel: {
      type: String,
      default: "",
    },
    actionDisabled: {
      type: Boolean,
      default: false,
    },
    actionLoading: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    clampedProgress() {
      const parsed = Number(this.progress || 0);
      if (!Number.isFinite(parsed)) {
        return 0;
      }
      return Math.max(0, Math.min(100, Math.round(parsed)));
    },
    progressStyle() {
      return `width:${this.clampedProgress}%;`;
    },
    toneClass() {
      const tone = String(this.tone || "info").toLowerCase();
      if (tone === "success") {
        return "task-card-success";
      }
      if (tone === "warning") {
        return "task-card-warning";
      }
      if (tone === "danger" || tone === "error") {
        return "task-card-danger";
      }
      return "task-card-info";
    },
  },
};
</script>

<style scoped>
.task-card {
  padding: 24rpx;
  border-radius: 20rpx;
  border: 1rpx solid transparent;
}

.task-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14rpx;
}

.task-main {
  flex: 1;
  min-width: 0;
}

.task-title {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
}

.task-status {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
}

.task-action {
  min-width: 132rpx;
  height: 62rpx;
  line-height: 62rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.task-action::after {
  display: none;
}

.task-progress-track {
  margin-top: 16rpx;
  width: 100%;
  height: 10rpx;
  border-radius: 999rpx;
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  border-radius: 999rpx;
}

.task-progress-text,
.task-message,
.task-hint {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.7;
}

.task-card-info {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.task-card-info .task-title,
.task-card-info .task-status {
  color: #1d4ed8;
}

.task-card-info .task-progress-track {
  background: #dbeafe;
}

.task-card-info .task-progress-fill {
  background: linear-gradient(90deg, #3b82f6, #2563eb);
}

.task-card-info .task-progress-text,
.task-card-info .task-message,
.task-card-info .task-hint {
  color: #1e3a8a;
}

.task-card-info .task-action {
  background: #dbeafe;
  color: #1d4ed8;
}

.task-card-warning {
  background: #fff7ed;
  border-color: #fed7aa;
}

.task-card-warning .task-title,
.task-card-warning .task-status {
  color: #c2410c;
}

.task-card-warning .task-progress-track {
  background: #ffedd5;
}

.task-card-warning .task-progress-fill {
  background: linear-gradient(90deg, #f97316, #ea580c);
}

.task-card-warning .task-progress-text,
.task-card-warning .task-message,
.task-card-warning .task-hint {
  color: #9a3412;
}

.task-card-warning .task-action {
  background: #ffedd5;
  color: #c2410c;
}

.task-card-danger {
  background: #fef2f2;
  border-color: #fecaca;
}

.task-card-danger .task-title,
.task-card-danger .task-status {
  color: #b91c1c;
}

.task-card-danger .task-progress-track {
  background: #fee2e2;
}

.task-card-danger .task-progress-fill {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.task-card-danger .task-progress-text,
.task-card-danger .task-message,
.task-card-danger .task-hint {
  color: #991b1b;
}

.task-card-danger .task-action {
  background: #fee2e2;
  color: #b91c1c;
}

.task-card-success {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.task-card-success .task-title,
.task-card-success .task-status {
  color: #15803d;
}

.task-card-success .task-progress-track {
  background: #dcfce7;
}

.task-card-success .task-progress-fill {
  background: linear-gradient(90deg, #22c55e, #16a34a);
}

.task-card-success .task-progress-text,
.task-card-success .task-message,
.task-card-success .task-hint {
  color: #166534;
}

.task-card-success .task-action {
  background: #dcfce7;
  color: #15803d;
}
</style>
