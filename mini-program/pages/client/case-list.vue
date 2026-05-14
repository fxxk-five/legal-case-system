<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="hero-kicker">{{ textMap.kicker }}</text>
      <text class="page-hero-title">{{ textMap.title }}</text>
      <text class="page-hero-desc">{{ textMap.description }}</text>
    </view>

    <view class="card">
      <text class="section-title">{{ textMap.sectionTitle }}</text>
      <text class="meta">{{ caseCountText }}</text>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-primary action-button" @click="loadCases">{{ textMap.refresh }}</button>
      </view>
    </view>

    <view v-if="loading" class="card empty-state">{{ textMap.loading }}</view>
    <view v-else-if="!cases.length" class="card empty-state">{{ textMap.empty }}</view>

    <view v-for="item in cases" :key="item.id" class="card case-card" @click="goDetail(item.id)">
      <view class="row-between row-top">
        <view>
          <text class="list-card-title">{{ item.title }}</text>
          <text class="list-card-subtitle">{{ item.case_number_text }}</text>
        </view>
        <view class="tag-wrap">
          <view v-if="item.hasNewUpdate" class="new-dot" />
          <text class="tag" :style="item.reminder_style">{{ item.reminder_text }}</text>
        </view>
      </view>
      <text class="meta">{{ item.legal_type_text }} · {{ item.stage_text }}</text>
      <text class="meta">{{ item.deadline_text }} · {{ item.updated_at_text }}</text>
    </view>

    <client-tab-bar current-key="cases" />
  </view>
</template>

<script>
import ClientTabBar from "../../components/ClientTabBar.vue";
import { formatAnalysisStatus, formatDateTime, formatLegalType, getDeadlineReminder } from "../../shared/lib/display";
import { resolveCaseStage } from "../../entities/case/policy";
import { get } from "../../shared/api/http";
import { friendlyError, showFormError } from "../../shared/lib/form";
import { buildClientCaseDetailUrl } from "../../features/auth/role-routing";
import { ensureClientAccess } from "../../features/auth/session";

export default {
  components: {
    ClientTabBar,
  },
  data() {
    return {
      loading: false,
      cases: [],
      textMap: {
        kicker: "\u6848\u4ef6",
        title: "\u6211\u7684\u6848\u4ef6",
        description: "\u4ec5\u5c55\u793a\u4e0e\u4f60\u76f8\u5173\u7684\u6848\u4ef6\u3002",
        sectionTitle: "\u6982\u89c8",
        refresh: "\u5237\u65b0\u5217\u8868",
        loading: "\u6b63\u5728\u52a0\u8f7d\u6848\u4ef6...",
        empty: "\u6682\u65e0\u53ef\u67e5\u770b\u6848\u4ef6\u3002",
      },
    };
  },
  computed: {
    caseCountText() {
      return `\u5f53\u524d\u5171 ${this.cases.length} \u4e2a\u6848\u4ef6`;
    },
  },
  onShow() {
    if (!ensureClientAccess()) return;
    this.loadCases();
  },
  methods: {
    decorateCase(item) {
      const reminder = getDeadlineReminder(item);
      const stage = resolveCaseStage(item);
      const lastViewed = uni.getStorageSync(`lastViewed_${item.id}`) || 0;
      const hasNewUpdate = item.updated_at && new Date(item.updated_at).getTime() > Number(lastViewed);
      return {
        ...item,
        case_number_text: item.case_number || "-",
        legal_type_text: formatLegalType(item.legal_type),
        analysis_text: formatAnalysisStatus(item.analysis_status, item.analysis_progress),
        stage_text: stage.label,
        deadline_text: formatDateTime(item.deadline, "-"),
        updated_at_text: formatDateTime(item.updated_at, "-"),
        reminder_text: reminder.text,
        reminder_style: reminder.style,
        hasNewUpdate,
      };
    },
    async loadCases() {
      this.loading = true;
      try {
        const list = await get("/cases");
        const items = Array.isArray(list) ? list.map((item) => this.decorateCase(item)) : [];
        this.cases = items;
      } catch (error) {
        showFormError(friendlyError(error, "\u52a0\u8f7d\u6848\u4ef6\u5931\u8d25"));
      } finally {
        this.loading = false;
      }
    },
    goDetail(caseId) {
      uni.setStorageSync(`lastViewed_${caseId}`, Date.now());
      uni.navigateTo({ url: buildClientCaseDetailUrl(caseId) });
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

.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.row-top {
  align-items: flex-start;
}

.tag-wrap {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-shrink: 0;
}

.new-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: #ef4444;
  flex-shrink: 0;
}
</style>


