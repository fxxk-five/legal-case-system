<template>
  <view class="page-container">
    <view class="card header-card">
      <text class="header-title">律师工作台</text>
      <text class="header-desc">展示当前租户案件列表，后续可继续补筛选、拖拽、通知提醒。</text>
      <button class="primary-btn" @click="goCreateCase">新建案件</button>
    </view>

    <view class="section-title">案件列表</view>
    <view v-if="!cases.length" class="card empty-card">
      <text>当前还没有案件，先创建一个案件开始演示。</text>
    </view>
    <view
      v-for="item in cases"
      :key="item.id"
      class="card case-card"
      @click="goDetail(item.id)"
    >
      <text class="case-number">{{ item.case_number }}</text>
      <text class="case-title">{{ item.title }}</text>
      <text class="case-meta">状态：{{ item.status }}</text>
      <text class="case-meta">当事人：{{ item.client?.real_name || '未关联' }}</text>
    </view>
  </view>
</template>

<script setup>
import { onShow } from "@dcloudio/uni-app";
import { ref } from "vue";

import { get } from "../../common/http";
import { requireLogin } from "../../common/session";

const cases = ref([]);

async function loadCases() {
  try {
    cases.value = await get("/cases");
  } catch (error) {
    uni.showToast({ title: error.detail || "获取案件失败", icon: "none" });
  }
}

function goCreateCase() {
  uni.navigateTo({ url: "/pages/lawyer/create-case" });
}

function goDetail(id) {
  uni.navigateTo({ url: `/pages/lawyer/case-detail?id=${id}` });
}

onShow(() => {
  if (!requireLogin()) {
    return;
  }
  loadCases();
});
</script>

<style scoped>
.header-card {
  background: linear-gradient(135deg, #1e293b, #0f766e);
  color: #fff;
  margin-bottom: 24rpx;
}

.header-title,
.case-title {
  display: block;
  font-size: 34rpx;
  font-weight: 600;
}

.header-desc,
.case-meta,
.case-number {
  display: block;
  margin-top: 12rpx;
}

.case-card {
  margin-bottom: 20rpx;
}

.case-number {
  color: #2563eb;
  font-size: 24rpx;
}

.primary-btn {
  margin-top: 24rpx;
  width: 100%;
  height: 84rpx;
  border-radius: 18rpx;
  background: #fff;
  color: #0f172a;
}

.empty-card {
  color: #64748b;
}
</style>
