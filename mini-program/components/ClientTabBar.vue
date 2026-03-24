<template>
  <view class="workspace-tabbar">
    <view class="workspace-tabbar-inner">
      <view
        v-for="item in items"
        :key="item.key"
        class="workspace-tabbar-item"
        :class="{ 'workspace-tabbar-item-active': item.current }"
        @click="handleTap(item)"
      >
        <text v-if="item.current" class="workspace-tabbar-dot"></text>
        <text class="workspace-tabbar-label">{{ item.label }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import { buildClientMenu, openWorkspacePage } from "../common/workspace";

export default {
  name: "ClientTabBar",
  props: {
    currentKey: {
      type: String,
      default: "",
    },
  },
  computed: {
    items() {
      return buildClientMenu(this.currentKey);
    },
  },
  methods: {
    handleTap(item) {
      if (!item || item.current || !item.path) {
        return;
      }
      openWorkspacePage(item.path);
    },
  },
};
</script>

<style scoped>
.workspace-tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  padding: 0 20rpx calc(18rpx + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, rgba(245, 245, 247, 0), rgba(245, 245, 247, 0.94) 24%, #f5f5f7 100%);
  box-sizing: border-box;
}

.workspace-tabbar-inner {
  display: flex;
  align-items: stretch;
  gap: 8rpx;
  padding: 10rpx;
  border: 1rpx solid rgba(29, 29, 31, 0.06);
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(20rpx);
}

.workspace-tabbar-item {
  flex: 1;
  min-height: 84rpx;
  padding: 12rpx 8rpx;
  border-radius: 999rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  box-sizing: border-box;
}

.workspace-tabbar-item-active {
  background: rgba(0, 113, 227, 0.1);
}

.workspace-tabbar-dot {
  width: 8rpx;
  height: 8rpx;
  border-radius: 50%;
  background: #0071e3;
}

.workspace-tabbar-label {
  color: #6e6e73;
  font-size: 24rpx;
  font-weight: 600;
  text-align: center;
  line-height: 1.4;
}

.workspace-tabbar-item-active .workspace-tabbar-label {
  color: #1d1d1f;
}
</style>
