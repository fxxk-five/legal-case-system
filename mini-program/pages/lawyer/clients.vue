<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">当事人管理</text>
      <text class="page-hero-desc">
        小程序律师端与网页端共用同一套当事人接口，支持列表筛选、详情查看、资料编辑，以及从当事人详情回跳案件详情。
      </text>

    </view>

    <template v-if="!isDetailMode">
      <view class="card">
        <text class="section-title">筛选与排序</text>
        <input
          v-model="keyword"
          class="input search-input"
          maxlength="100"
          placeholder="搜索当事人姓名或手机号"
          confirm-type="search"
          @confirm="handleSearch"
        />
        <picker class="picker-wrap" :range="sortOptions" range-key="label" :value="sortIndex" @change="onSortChange">
          <view class="picker-input">{{ sortLabel }}</view>
        </picker>
        <view class="toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" @click="handleSearch">查询</button>
          <button class="toolbar-button toolbar-button-secondary action-button" @click="resetFilters">重置</button>
        </view>
      </view>

      <view class="card">
        <text class="section-title">列表概览</text>
        <text class="meta">{{ clientCountText }}</text>
        <text class="meta">点击某位当事人后，可查看完整资料、编辑手机号，并直接进入其关联案件详情。</text>
      </view>

      <view v-if="loadingList" class="card empty-state">正在加载当事人列表...</view>
      <view v-else-if="!clients.length" class="card empty-state">暂无符合条件的当事人。</view>

      <view v-for="item in clients" :key="item.id" class="card client-card">
        <text class="list-card-title">{{ item.real_name }}</text>
        <text class="list-card-subtitle">{{ item.phone }}</text>
        <text class="meta">关联案件：{{ item.case_count }} 件</text>
        <text class="meta">创建时间：{{ item.created_at_text }}</text>
        <text class="meta">最后上传：{{ item.last_uploaded_at_text }}</text>
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-secondary action-button" @click="openClientDetail(item.id)">查看详情</button>
        </view>
      </view>
    </template>

    <template v-else>
      <view v-if="loadingDetail && !detail" class="card empty-state">正在加载当事人详情...</view>

      <template v-else-if="detail">
        <view class="card">
          <text class="section-title">{{ detail.real_name }}</text>
          <text class="list-card-subtitle">{{ detail.phone }}</text>
          <text class="meta">关联案件：{{ detailCaseCountText }}</text>
          <text class="meta">创建时间：{{ detail.created_at_text }}</text>
          <text class="meta">最后上传：{{ detail.last_uploaded_at_text }}</text>
          <view class="toolbar card-toolbar">
            <button class="toolbar-button toolbar-button-secondary action-button" @click="backToList">返回列表</button>
            <button class="toolbar-button toolbar-button-primary action-button" :loading="saving" @click="saveClient">保存资料</button>
          </view>
        </view>

        <view class="card">
          <text class="section-title">基础信息编辑</text>
          <input v-model="editForm.real_name" class="input field-gap" maxlength="100" placeholder="当事人姓名" />
          <input v-model="editForm.phone" class="input field-gap" maxlength="11" placeholder="当事人手机号" />
          <text class="meta">修改后会同步更新网页端与小程序端显示。</text>
        </view>

        <view class="card">
          <text class="section-title">关联案件</text>
          <view v-if="!detail.cases.length" class="empty-state">当前没有可见案件。</view>
          <view v-for="item in detail.cases" :key="item.id" class="case-card">
            <text class="list-card-title">{{ item.title }}</text>
            <text class="list-card-subtitle">{{ item.case_number || '未生成案号' }}</text>
            <text class="meta">法律类型：{{ item.legal_type_text }}</text>
            <text class="meta">案件状态：{{ item.status_text }}</text>
            <text class="meta">负责律师：{{ item.lawyer_name }}</text>
            <text class="meta">截止时间：{{ item.deadline_text }}</text>
            <text class="meta">最近更新：{{ item.updated_at_text }}</text>
            <view class="case-footer">
              <text class="tag" :style="item.reminder_style">{{ item.reminder_text }}</text>
              <button class="toolbar-button toolbar-button-secondary case-action" @click="openCase(item.id)">打开案件</button>
            </view>
          </view>
        </view>
      </template>

      <view v-else class="card empty-state">
        当前未找到该当事人，可能已被移除或你无权访问。
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-secondary action-button" @click="backToList">返回列表</button>
        </view>
      </view>
    </template>

    <workspace-tab-bar current-key="clients" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { buildWorkspaceCaseDetailUrl, buildWorkspaceClientDetailUrl, getWorkspaceModuleUrl } from "../../common/role-routing";
import {
  formatCaseStatus,
  formatDateTime,
  formatLegalType,
  formatText,
  getDeadlineReminder,
} from "../../common/display";
import { buildQuery, get, patch } from "../../common/http";
import { friendlyError, showFormError, validateName, validatePhone } from "../../common/form";
import { ensureWorkspaceAccess } from "../../common/workspace";

const SORT_OPTIONS = [
  { label: "按创建时间（最新）", value: "created_at_desc" },
  { label: "按姓名（A-Z）", value: "real_name_asc" },
  { label: "按手机号（升序）", value: "phone_asc" },
  { label: "按案件数量（最多）", value: "case_count_desc" },
  { label: "按最后上传（最新）", value: "last_uploaded_at_desc" },
];

function splitSortValue(value) {
  const source = String(value || "created_at_desc");
  const index = source.lastIndexOf("_");
  if (index <= 0) {
    return { sort_by: "created_at", sort_order: "desc" };
  }
  return {
    sort_by: source.slice(0, index),
    sort_order: source.slice(index + 1),
  };
}

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      loadingList: false,
      loadingDetail: false,
      saving: false,
      detailId: 0,
      keyword: "",
      sortOptions: SORT_OPTIONS,
      sortIndex: 0,
      clients: [],
      detail: null,
      editForm: {
        real_name: "",
        phone: "",
      },
    };
  },
  computed: {
    isDetailMode() {
      return Boolean(this.detailId);
    },
    sortLabel() {
      const current = this.sortOptions[this.sortIndex];
      return current ? current.label : "按创建时间（最新）";
    },
    clientCountText() {
      return `当前共 ${this.clients.length} 位当事人`;
    },
    detailCaseCountText() {
      if (!this.detail || !Array.isArray(this.detail.cases)) {
        return "0 件";
      }
      return `${this.detail.cases.length} 件`;
    },
  },
  onLoad(options) {
    const clientId = Number(options.id || 0);
    this.detailId = Number.isNaN(clientId) ? 0 : clientId;
  },
  onShow() {
    const user = ensureWorkspaceAccess();
    if (!user) {
      return;
    }
    this.refreshPage();
  },
  methods: {
    decorateClient(item) {
      return {
        ...item,
        created_at_text: formatDateTime(item.created_at, "-"),
        last_uploaded_at_text: formatDateTime(item.last_uploaded_at, "暂无上传"),
      };
    },
    decorateCase(item) {
      const reminder = getDeadlineReminder(item);
      return {
        ...item,
        legal_type_text: formatLegalType(item.legal_type),
        status_text: formatCaseStatus(item.status),
        lawyer_name: formatText(item.assigned_lawyer_name, "未分配"),
        deadline_text: formatDateTime(item.deadline, "未设置"),
        updated_at_text: formatDateTime(item.updated_at, "-"),
        reminder_text: reminder.text,
        reminder_style: reminder.style,
      };
    },
    refreshPage() {
      if (this.isDetailMode) {
        this.loadDetail();
        return;
      }
      this.loadClients();
    },
    async loadClients() {
      this.loadingList = true;
      try {
        const currentSort = this.sortOptions[this.sortIndex] || this.sortOptions[0];
        const sort = splitSortValue(currentSort.value);
        const params = {
          q: this.keyword.trim() || undefined,
          sort_by: sort.sort_by,
          sort_order: sort.sort_order,
        };
        const list = await get(`/clients${buildQuery(params)}`);
        this.clients = Array.isArray(list) ? list.map((item) => this.decorateClient(item)) : [];
      } catch (error) {
        showFormError(friendlyError(error, "加载当事人列表失败"));
      } finally {
        this.loadingList = false;
      }
    },
    async loadDetail() {
      if (!this.detailId) {
        return;
      }
      this.loadingDetail = true;
      try {
        const detail = await get(`/clients/${this.detailId}`);
        this.detail = {
          ...this.decorateClient(detail),
          cases: Array.isArray(detail.cases) ? detail.cases.map((item) => this.decorateCase(item)) : [],
        };
        this.editForm.real_name = this.detail.real_name || "";
        this.editForm.phone = this.detail.phone || "";
      } catch (error) {
        this.detail = null;
        showFormError(friendlyError(error, "加载当事人详情失败"));
      } finally {
        this.loadingDetail = false;
      }
    },
    openClientDetail(clientId) {
      uni.navigateTo({ url: buildWorkspaceClientDetailUrl(clientId) });
    },
    backToList() {
      this.detail = null;
      this.editForm.real_name = "";
      this.editForm.phone = "";
      if (getCurrentPages().length > 1) {
        uni.navigateBack({ delta: 1 });
        return;
      }
      uni.redirectTo({ url: getWorkspaceModuleUrl("clients") });
    },
    openCase(caseId) {
      const clientId = this.detail ? this.detail.id : this.detailId;
      uni.navigateTo({ url: buildWorkspaceCaseDetailUrl(caseId, { from: "client", clientId }) });
    },
    handleSearch() {
      if (this.isDetailMode) {
        return;
      }
      this.loadClients();
    },
    resetFilters() {
      this.keyword = "";
      this.sortIndex = 0;
      this.loadClients();
    },
    onSortChange(event) {
      this.sortIndex = Number(event.detail.value || 0);
      this.loadClients();
    },
    async saveClient() {
      const message =
        validateName(this.editForm.real_name, "当事人姓名") ||
        validatePhone(this.editForm.phone, "当事人手机号");
      if (message) {
        showFormError(message);
        return;
      }
      if (!this.detailId) {
        return;
      }

      this.saving = true;
      try {
        await patch(`/clients/${this.detailId}`, {
          real_name: this.editForm.real_name.trim(),
          phone: this.editForm.phone.trim(),
        });
        uni.showToast({ title: "已保存", icon: "success" });
        await this.loadDetail();
      } catch (error) {
        showFormError(friendlyError(error, "保存当事人资料失败"));
      } finally {
        this.saving = false;
      }
    },
  },
};
</script>

<style scoped>
.search-input,
.picker-wrap,
.field-gap {
  margin-bottom: 18rpx;
}

.client-card,
.case-card {
  margin-bottom: 20rpx;
}

.card-toolbar {
  margin-top: 18rpx;
}

.action-button,
.case-action {
  width: 100%;
}

.case-card {
  padding: 24rpx 0;
  border-top: 1rpx solid #e2e8f0;
}

.case-card:first-of-type {
  border-top: 0;
  padding-top: 8rpx;
}

.case-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 18rpx;
}
</style>
