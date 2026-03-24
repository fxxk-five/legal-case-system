<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="hero-kicker">案件</text>
      <text class="page-hero-title">{{ pageTitle }}</text>
      <text class="page-hero-desc">{{ pageDescription }}</text>
    </view>

    <view class="card">
      <text class="section-title">筛选与排序</text>

      <input
        v-model="keyword"
        class="input search-input"
        maxlength="100"
        placeholder="搜索标题或案号"
        confirm-type="search"
        @confirm="handleSearch"
      />

      <picker class="picker-wrap" :range="statusOptions" range-key="label" :value="statusIndex" @change="onStatusChange">
        <view class="picker-input">{{ statusLabel }}</view>
      </picker>

      <picker class="picker-wrap" :range="legalTypeOptions" range-key="label" :value="legalTypeIndex" @change="onLegalTypeChange">
        <view class="picker-input">{{ legalTypeLabel }}</view>
      </picker>

      <picker class="picker-wrap" :range="sortOptions" range-key="label" :value="sortIndex" @change="onSortChange">
        <view class="picker-input">{{ sortLabel }}</view>
      </picker>

      <view class="toolbar">
        <button class="toolbar-button toolbar-button-primary filter-button" @click="handleSearch">查询</button>
        <button class="toolbar-button toolbar-button-secondary filter-button" @click="resetFilters">重置</button>
      </view>
    </view>

    <view class="card">
      <view class="toolbar">
        <button class="toolbar-button toolbar-button-primary filter-button" @click="goCreateCase">{{ createCaseLabel }}</button>
        <button class="toolbar-button toolbar-button-secondary filter-button" @click="loadCases">刷新列表</button>
      </view>
      <text class="meta">{{ caseSummaryText }}</text>
    </view>

    <view v-if="loading" class="card empty-state">正在加载案件列表...</view>
    <view v-else-if="!cases.length" class="card empty-state">暂无匹配案件。</view>

    <view v-for="item in cases" :key="item.id" class="card case-card" @click="goDetail(item.id)">
      <view class="case-card-head">
        <view class="case-main">
          <text class="list-card-title">{{ item.title }}</text>
          <text class="list-card-subtitle">{{ item.case_number }}</text>
        </view>
        <text class="tag" :style="item.reminder_style">{{ item.reminder_text }}</text>
      </view>
      <text class="meta">法律类型：{{ item.legal_type_text }}</text>
      <text class="meta">当事人：{{ item.client_name }}</text>
      <text class="meta">状态：{{ item.status_text }}</text>
      <text class="meta">截止时间：{{ item.deadline_text }}</text>
      <text class="meta">解析状态：{{ item.analysis_text }}</text>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { buildCreateCaseUrl, buildWorkspaceCaseDetailUrl } from "../../common/role-routing";
import {
  CASE_SORT_OPTIONS,
  CASE_STATUS_OPTIONS,
  LEGAL_TYPE_OPTIONS,
  formatAnalysisStatus,
  formatCaseStatus,
  formatDateTime,
  formatLegalType,
  formatText,
  getDeadlineReminder,
} from "../../common/display";
import { get } from "../../common/http";
import { friendlyError, showFormError } from "../../common/form";
import { ensureWorkspaceAccess } from "../../common/workspace";

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      loading: false,
      currentUser: null,
      keyword: "",
      statusOptions: CASE_STATUS_OPTIONS,
      legalTypeOptions: LEGAL_TYPE_OPTIONS,
      sortOptions: CASE_SORT_OPTIONS,
      statusIndex: 0,
      legalTypeIndex: 0,
      sortIndex: 0,
      cases: [],
    };
  },
  computed: {
    isPersonalWorkspace() {
      return String(this.currentUser?.tenant_type || "") === "personal";
    },
    pageTitle() {
      return this.isPersonalWorkspace ? "我的案件" : "案件管理";
    },
    pageDescription() {
      return this.isPersonalWorkspace ? "快速继续处理你的案件。" : "支持筛选、排序并进入详情。";
    },
    createCaseLabel() {
      return this.isPersonalWorkspace ? "新建我的案件" : "新建案件";
    },
    caseSummaryText() {
      return `当前显示 ${this.cases.length} 个案件`;
    },
    statusLabel() {
      const current = this.statusOptions[this.statusIndex];
      return current ? current.label : "全部状态";
    },
    legalTypeLabel() {
      const current = this.legalTypeOptions[this.legalTypeIndex];
      return current ? current.label : "全部法律类型";
    },
    sortLabel() {
      const current = this.sortOptions[this.sortIndex];
      return current ? current.label : "最新优先";
    },
    currentStatus() {
      return this.statusOptions[this.statusIndex] ? this.statusOptions[this.statusIndex].value : "";
    },
    currentLegalType() {
      return this.legalTypeOptions[this.legalTypeIndex] ? this.legalTypeOptions[this.legalTypeIndex].value : "";
    },
    currentSortValue() {
      return this.sortOptions[this.sortIndex] ? this.sortOptions[this.sortIndex].value : "created_at_desc";
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
    buildCaseItem(item) {
      const reminder = getDeadlineReminder(item);
      return {
        ...item,
        client_name: formatText(item.client ? item.client.real_name : "", "-"),
        status_text: formatCaseStatus(item.status),
        legal_type_text: formatLegalType(item.legal_type),
        deadline_text: formatDateTime(item.deadline, "-"),
        analysis_text: formatAnalysisStatus(item.analysis_status, item.analysis_progress),
        reminder_text: reminder.text,
        reminder_style: reminder.style,
      };
    },
    buildParams() {
      const sortValue = this.currentSortValue || "created_at_desc";
      const splitIndex = sortValue.lastIndexOf("_");
      const sortBy = splitIndex > 0 ? sortValue.slice(0, splitIndex) : "created_at";
      const sortOrder = splitIndex > 0 ? sortValue.slice(splitIndex + 1) : "desc";

      return {
        page: 1,
        page_size: 100,
        status: this.currentStatus || undefined,
        legal_type: this.currentLegalType || undefined,
        q: this.keyword.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
    },
    async loadCases() {
      this.loading = true;
      try {
        const params = this.buildParams();
        const query = Object.keys(params)
          .filter((key) => params[key] !== undefined && params[key] !== "")
          .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`)
          .join("&");
        const list = await get(`/cases${query ? `?${query}` : ""}`);
        this.cases = Array.isArray(list) ? list.map(this.buildCaseItem) : [];
      } catch (error) {
        showFormError(friendlyError(error, "加载案件列表失败"));
      } finally {
        this.loading = false;
      }
    },
    onStatusChange(event) {
      this.statusIndex = Number(event.detail.value || 0);
      this.loadCases();
    },
    onLegalTypeChange(event) {
      this.legalTypeIndex = Number(event.detail.value || 0);
      this.loadCases();
    },
    onSortChange(event) {
      this.sortIndex = Number(event.detail.value || 0);
      this.loadCases();
    },
    handleSearch() {
      this.loadCases();
    },
    resetFilters() {
      this.keyword = "";
      this.statusIndex = 0;
      this.legalTypeIndex = 0;
      this.sortIndex = 0;
      this.loadCases();
    },
    goCreateCase() {
      uni.navigateTo({ url: buildCreateCaseUrl() });
    },
    goDetail(id) {
      uni.navigateTo({ url: buildWorkspaceCaseDetailUrl(id) });
    },
  },
};
</script>

<style scoped>
.search-input,
.picker-wrap {
  margin-bottom: 18rpx;
}

.filter-button {
  width: 100%;
}

.case-card {
  margin-bottom: 20rpx;
}

.case-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}

.case-main {
  flex: 1;
  min-width: 0;
}
</style>
