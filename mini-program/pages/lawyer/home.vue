<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">{{ pageTitle }}</text>
      <text class="page-hero-desc">{{ pageDescription }}</text>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-primary action-button" @click="goCreateCase">新建案件</button>
        <button class="toolbar-button toolbar-button-secondary action-button" @click="loadCases">刷新列表</button>
        <button v-if="canOpenAnalytics" class="toolbar-button toolbar-button-secondary action-button" @click="goAnalytics">
          分析管理
        </button>
      </view>
    </view>

    <view class="card">
      <text class="section-title">案件概览</text>
      <text class="meta">当前共 {{ cases.length }} 个案件</text>
      <text class="meta">点击案件卡片可进入详情，并继续邀请当事人、查看时间流和材料。</text>
    </view>

    <view v-if="loading" class="card empty-state">正在加载案件列表...</view>
    <view v-else-if="!cases.length" class="card empty-state">当前还没有案件，先创建一个开始处理。</view>

    <view v-for="item in cases" :key="item.id" class="card case-card" @click="goDetail(item.id)">
      <text class="case-number">{{ item.case_number || "未生成案号" }}</text>
      <text class="case-title">{{ item.title }}</text>
      <text class="case-meta">状态：{{ formatCaseStatus(item.status) }}</text>
      <text class="case-meta">当事人：{{ formatText(item.client ? item.client.real_name : "", "未关联") }}</text>
    </view>

    <workspace-tab-bar :current-key="currentMenuKey" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { formatCaseStatus, formatText, isTenantAdmin } from "../../common/display";
import { friendlyError, showFormError } from "../../common/form";
import { get } from "../../common/http";
import { ensureWorkspaceAccess } from "../../common/workspace";

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      currentUser: null,
      loading: false,
      cases: [],
    };
  },
  computed: {
    isPersonalWorkspace() {
      return String(this.currentUser?.tenant_type || "") === "personal";
    },
    canOpenAnalytics() {
      return !this.isPersonalWorkspace && isTenantAdmin(this.currentUser);
    },
    currentMenuKey() {
      return this.isPersonalWorkspace ? "cases" : "overview";
    },
    pageTitle() {
      return this.isPersonalWorkspace ? "我的案件" : "律师工作台";
    },
    pageDescription() {
      return this.isPersonalWorkspace
        ? "这里展示你可见的案件列表，并保留“案件管理 / 我的”两个入口。"
        : "这里展示机构案件概览，可继续进入案件、当事人、律师与我的页面。";
    },
  },
  onShow() {
    const user = ensureWorkspaceAccess();
    if (!user) {
      return;
    }
    this.currentUser = user;
    this.loadCases();
  },
  methods: {
    formatCaseStatus,
    formatText,
    async loadCases() {
      this.loading = true;
      try {
        const list = await get("/cases");
        this.cases = Array.isArray(list) ? list : [];
      } catch (error) {
        showFormError(friendlyError(error, "获取案件失败"));
      } finally {
        this.loading = false;
      }
    },
    goCreateCase() {
      uni.navigateTo({ url: "/pages/lawyer/create-case" });
    },
    goAnalytics() {
      uni.navigateTo({ url: "/pages/lawyer/analytics" });
    },
    goDetail(id) {
      uni.navigateTo({ url: `/pages/lawyer/case-detail?id=${id}` });
    },
  },
};
</script>

<style scoped>
.card-toolbar {
  margin-top: 18rpx;
}

.action-button {
  width: 100%;
}

.case-card {
  margin-bottom: 20rpx;
}

.case-number {
  display: block;
  color: #2563eb;
  font-size: 24rpx;
}

.case-title {
  display: block;
  margin-top: 10rpx;
  font-size: 34rpx;
  font-weight: 600;
  color: #0f172a;
}

.case-meta {
  display: block;
  margin-top: 12rpx;
}
</style>
