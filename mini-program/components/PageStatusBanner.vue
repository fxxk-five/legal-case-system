<template>
  <view class="status-banner" :class="toneClass">
    <view class="status-main">
      <text class="status-title">{{ title }}</text>
      <text v-if="message" class="status-message">{{ message }}</text>
    </view>
    <button v-if="actionLabel" class="status-action" @click="$emit('action')">{{ actionLabel }}</button>
  </view>
</template>

<script>
export default {
  name: "PageStatusBanner",
  props: {
    tone: {
      type: String,
      default: "info",
    },
    title: {
      type: String,
      default: "",
    },
    message: {
      type: String,
      default: "",
    },
    actionLabel: {
      type: String,
      default: "",
    },
  },
  computed: {
    toneClass() {
      const tone = String(this.tone || "info").toLowerCase();
      if (tone === "success") {
        return "status-banner-success";
      }
      if (tone === "warning") {
        return "status-banner-warning";
      }
      if (tone === "danger" || tone === "error") {
        return "status-banner-danger";
      }
      return "status-banner-info";
    },
  },
};
</script>

<style scoped>
.status-banner {
  display: flex;
  gap: 16rpx;
  align-items: center;
  justify-content: space-between;
  padding: 22rpx 24rpx;
  border-radius: 20rpx;
  border: 1rpx solid transparent;
}

.status-main {
  flex: 1;
  min-width: 0;
}

.status-title {
  display: block;
  color: #0f172a;
  font-size: 28rpx;
  font-weight: 600;
}

.status-message {
  display: block;
  margin-top: 8rpx;
  color: #334155;
  font-size: 24rpx;
  line-height: 1.7;
}

.status-action {
  min-width: 132rpx;
  height: 62rpx;
  line-height: 62rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.status-action::after {
  display: none;
}

.status-banner-info {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.status-banner-info .status-title {
  color: #1d4ed8;
}

.status-banner-info .status-message {
  color: #1e3a8a;
}

.status-banner-info .status-action {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-banner-success {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.status-banner-success .status-title {
  color: #15803d;
}

.status-banner-success .status-message {
  color: #166534;
}

.status-banner-success .status-action {
  background: #dcfce7;
  color: #15803d;
}

.status-banner-warning {
  background: #fff7ed;
  border-color: #fed7aa;
}

.status-banner-warning .status-title {
  color: #c2410c;
}

.status-banner-warning .status-message {
  color: #9a3412;
}

.status-banner-warning .status-action {
  background: #ffedd5;
  color: #c2410c;
}

.status-banner-danger {
  background: #fef2f2;
  border-color: #fecaca;
}

.status-banner-danger .status-title {
  color: #b91c1c;
}

.status-banner-danger .status-message {
  color: #991b1b;
}

.status-banner-danger .status-action {
  background: #fee2e2;
  color: #b91c1c;
}
</style>
