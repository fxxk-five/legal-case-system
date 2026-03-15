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
  background: #f4f6f8;
  color: #1f2937;
  font-size: 28rpx;
}

.page-container {
  min-height: 100vh;
  padding: 32rpx;
  box-sizing: border-box;
}

.card {
  background: #ffffff;
  border-radius: 24rpx;
  padding: 28rpx;
  box-shadow: 0 12rpx 30rpx rgba(15, 23, 42, 0.06);
}

.section-title {
  font-size: 32rpx;
  font-weight: 600;
  margin-bottom: 24rpx;
}
</style>
