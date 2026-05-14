<template>
  <view class="failure-notice">
    <text class="failure-title">{{ title }}</text>
    <text class="failure-message">{{ message }}</text>
    <button class="failure-action" :disabled="disabled" @click="$emit('retry')">{{ actionLabel }}</button>
  </view>
</template>

<script>
export default {
  name: "UploadFailureNotice",
  props: {
    title: {
      type: String,
      default: "上传失败提醒",
    },
    message: {
      type: String,
      default: "",
    },
    actionLabel: {
      type: String,
      default: "继续上传",
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style scoped>
.failure-notice {
  margin-top: 16rpx;
  padding: 20rpx;
  border-radius: 20rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
}

.failure-title {
  display: block;
  color: #c2410c;
  font-size: 26rpx;
  font-weight: 700;
}

.failure-message {
  display: block;
  margin-top: 8rpx;
  color: #9a3412;
  font-size: 24rpx;
  line-height: 1.7;
}

.failure-action {
  margin-top: 14rpx;
  min-width: 160rpx;
  height: 62rpx;
  line-height: 62rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: #ffedd5;
  color: #c2410c;
  font-size: 22rpx;
}

.failure-action::after {
  display: none;
}
</style>
