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
      <view class="stats-row">
        <view class="stat-chip">
          <text class="stat-num">{{ cases.length }}</text>
          <text class="stat-label">全部案件</text>
        </view>
        <view class="stat-chip stat-chip-warning" v-if="urgentCount > 0">
          <text class="stat-num">{{ urgentCount }}</text>
          <text class="stat-label">临期待办</text>
        </view>
      </view>
      <text class="meta">点击案件卡片可进入详情，并继续邀请当事人、查看时间流和材料。</text>
    </view>

    <view v-if="loading" class="card empty-state">正在加载案件列表...</view>
    <view v-else-if="!cases.length" class="card empty-state">当前还没有案件，先创建一个开始处理。</view>

    <view v-for="item in cases" :key="item.id" class="card case-card" @click="goDetail(item.id)">
      <view class="case-header">
        <text class="case-number">{{ item.case_number || "未生成案号" }}</text>
        <view v-if="item.urgency_class" class="urgency-badge" :class="item.urgency_class">
          <text class="urgency-badge-text">{{ item.urgency_text }}</text>
        </view>
      </view>
      <text class="case-title">{{ item.title }}</text>
      <text class="case-meta">阶段：{{ item.stage_text }}</text>
      <text class="case-meta">当事人：{{ formatText(item.client ? item.client.real_name : "", "未关联") }}</text>
    </view>

    <workspace-tab-bar :current-key="currentMenuKey" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { formatText, isTenantAdmin } from "../../shared/lib/display";
import { resolveCaseStage } from "../../entities/case/policy";
import { friendlyError, showFormError } from "../../shared/lib/form";
import { get } from "../../shared/api/http";
import { ensureWorkspaceAccess } from "../../features/workspace/workspace";

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
    urgentCount() {
      const now = Date.now()
      return this.cases.filter((c) => {
        if (!c.deadline || c.status === 'done' || c.status === 'closed' || c.status === 'archived') return false
        const diffDays = Math.ceil((new Date(c.deadline).getTime() - now) / (24 * 60 * 60 * 1000))
        return diffDays <= 7
      }).length
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
    formatText,
    decorateCase(item) {
      const now = Date.now()
      let urgency_text = ''
      let urgency_class = ''
      if (item.deadline && item.status !== 'done' && item.status !== 'closed') {
        const diffDays = Math.ceil((new Date(item.deadline).getTime() - now) / (24 * 60 * 60 * 1000))
        if (diffDays < 0) {
          urgency_text = `逾期 ${Math.abs(diffDays)} 天`
          urgency_class = 'urgency-danger'
        } else if (diffDays <= 3) {
          urgency_text = `${diffDays} 天后到期`
          urgency_class = 'urgency-danger'
        } else if (diffDays <= 7) {
          urgency_text = `${diffDays} 天后到期`
          urgency_class = 'urgency-warning'
        }
      }
      return {
        ...item,
        stage_text: resolveCaseStage(item).label,
        urgency_text,
        urgency_class,
      };
    },
    async loadCases() {
      this.loading = true;
      try {
        const list = await get("/cases");
        this.cases = Array.isArray(list) ? list.map((item) => this.decorateCase(item)) : [];
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

.stats-row {
  display: flex;
  gap: 16rpx;
  margin: 12rpx 0 8rpx;
  flex-wrap: wrap;
}

.stat-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12rpx 28rpx;
  border-radius: 16rpx;
  background: #f1f5f9;
}

.stat-chip-warning {
  background: #fef3c7;
}

.stat-num {
  font-size: 40rpx;
  font-weight: 700;
  color: #0f172a;
}

.stat-chip-warning .stat-num {
  color: #b45309;
}

.stat-label {
  font-size: 22rpx;
  color: #64748b;
  margin-top: 4rpx;
}

.stat-chip-warning .stat-label {
  color: #92400e;
}

.case-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.urgency-badge {
  display: inline-flex;
  padding: 4rpx 14rpx;
  border-radius: 100rpx;
  flex-shrink: 0;
}

.urgency-danger {
  background: #fee2e2;
}

.urgency-warning {
  background: #fef3c7;
}

.urgency-badge-text {
  font-size: 22rpx;
  font-weight: 600;
}

.urgency-danger .urgency-badge-text {
  color: #b91c1c;
}

.urgency-warning .urgency-badge-text {
  color: #92400e;
}
</style>


