<script>
export default {
  onLaunch() {
    const token = uni.getStorageSync("access_token");
    if (token) {
      console.log("mini-program launch with token");
    }
  },
};
</script>

<style lang="scss">
page {
  --accent-color: #0071e3;
  --accent-soft: rgba(0, 113, 227, 0.1);
  --success-color: #248a3d;
  --warning-color: #b86e00;
  --danger-color: #c9342c;
  --bg-color: #f5f5f7;
  --surface-color: rgba(255, 255, 255, 0.92);
  --surface-strong: #ffffff;
  --surface-muted: #fbfbfd;
  --text-main: #1d1d1f;
  --text-sub: #6e6e73;
  --text-tertiary: #8e8e93;
  --border-color: rgba(29, 29, 31, 0.08);
  --radius-xl: 36rpx;
  --radius-lg: 28rpx;
  --radius-md: 22rpx;
  --shadow-soft: 0 20rpx 60rpx rgba(15, 23, 42, 0.06);

  background: linear-gradient(180deg, #fbfbfd 0%, #f5f5f7 100%);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
    "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB",
    "Microsoft Yahei", sans-serif;
  font-size: 28rpx;
  line-height: 1.5;
}

.page-container {
  min-height: 100vh;
  padding: 24rpx;
  box-sizing: border-box;
}

.workspace-page {
  padding-bottom: calc(180rpx + env(safe-area-inset-bottom));
}

.card,
.glass-card {
  background: var(--surface-color);
  border-radius: var(--radius-xl);
  padding: 28rpx;
  box-sizing: border-box;
  box-shadow: var(--shadow-soft);
  border: 1rpx solid var(--border-color);
  backdrop-filter: blur(20rpx);
  margin-bottom: 20rpx;
}

.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 16rpx;
}

.meta {
  display: block;
  margin-top: 8rpx;
  color: var(--text-sub);
  font-size: 24rpx;
  line-height: 1.6;
}

.page-hero {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(245, 245, 247, 0.92));
  border-color: rgba(0, 113, 227, 0.08);
}

.page-hero-title {
  display: block;
  font-size: 52rpx;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -1rpx;
}

.page-hero-desc {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: var(--text-sub);
}

.hero-kicker {
  display: block;
  margin-bottom: 10rpx;
  color: var(--text-tertiary);
  font-size: 22rpx;
  font-weight: 600;
  letter-spacing: 3rpx;
  text-transform: uppercase;
}

.workspace-menu {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.workspace-menu-item {
  min-width: 152rpx;
  padding: 14rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent-color);
  font-size: 22rpx;
  text-align: center;
  box-sizing: border-box;
}

.workspace-menu-item-active {
  background: rgba(0, 113, 227, 0.14);
  font-weight: 600;
}

.grid-two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.grid-three {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.stat-card-title {
  display: block;
  color: var(--text-sub);
  font-size: 22rpx;
}

.stat-card-value {
  display: block;
  margin-top: 10rpx;
  font-size: 42rpx;
  font-weight: 700;
  line-height: 1.1;
  color: var(--text-main);
}

.stat-card-desc {
  display: block;
  margin-top: 8rpx;
  color: var(--text-sub);
  font-size: 22rpx;
  line-height: 1.5;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.toolbar-button,
.primary-btn,
.ghost-btn {
  min-height: 84rpx;
  border-radius: 999rpx;
  font-size: 26rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 0 28rpx;
  border: 0;
}

.primary-btn,
.toolbar-button-primary {
  background: var(--text-main);
  color: #ffffff;
}

.ghost-btn,
.toolbar-button-secondary {
  background: rgba(255, 255, 255, 0.86);
  color: var(--text-main);
  border: 1rpx solid var(--border-color);
}

.input,
.picker-input {
  width: 100%;
  min-height: 88rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.78);
  border: 1rpx solid rgba(29, 29, 31, 0.06);
  box-sizing: border-box;
  color: var(--text-main);
}

.picker-input {
  line-height: 88rpx;
}

.tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 600;
  box-sizing: border-box;
}

.tag-neutral {
  color: #6e6e73;
  background: #ededf0;
}

.tag-success {
  color: #248a3d;
  background: rgba(52, 199, 89, 0.14);
}

.tag-warning {
  color: #b86e00;
  background: rgba(255, 159, 10, 0.16);
}

.tag-danger {
  color: #c9342c;
  background: rgba(255, 59, 48, 0.14);
}

.tag-primary {
  color: #0071e3;
  background: rgba(0, 113, 227, 0.12);
}

.empty-state {
  text-align: center;
  color: var(--text-sub);
  font-size: 24rpx;
  line-height: 1.6;
  padding: 28rpx 0;
}

.list-card-title {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
  line-height: 1.25;
  color: var(--text-main);
}

.list-card-subtitle {
  display: block;
  margin-top: 10rpx;
  color: var(--text-sub);
  font-size: 24rpx;
}

.divider {
  height: 1rpx;
  background: var(--border-color);
  margin: 18rpx 0;
}

.surface-arrow {
  flex-shrink: 0;
  color: #c7c7cc;
  font-size: 34rpx;
  line-height: 1;
}

.fade-in {
  animation: fadeIn 0.35s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(16rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
