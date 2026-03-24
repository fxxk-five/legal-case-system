<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">律师管理</text>
      <text class="page-hero-desc">
        仅机构管理员与超级管理员可访问，支持邀请机构律师、审批待加入成员，以及启用/停用现有律师账号。
      </text>

    </view>

    <template v-if="!isDetailMode">
      <view class="card">
        <text class="section-title">邀请入口</text>
        <text class="meta">生成邀请后，可将登录路径发给待加入律师。对方会直接进入微信快捷登录，不再走短信邀请码注册。</text>
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" :loading="inviteLoading" @click="generateInvite">生成邀请码</button>
          <button class="toolbar-button toolbar-button-secondary action-button" :disabled="!invitePath" @click="copyInvite">复制路径</button>
        </view>
        <view v-if="inviteToken" class="invite-box">
          <text class="meta">邀请码：{{ inviteToken }}</text>
          <text class="meta">小程序路径：{{ invitePath }}</text>
        </view>
      </view>

      <view class="card">
        <text class="section-title">成员概览</text>
        <text class="meta">已启用/停用律师：{{ lawyers.length }} 人</text>
        <text class="meta">待审批成员：{{ pendingUsers.length }} 人</text>
      </view>

      <view class="card">
        <text class="section-title">搜索成员</text>
        <input
          v-model="keyword"
          class="input search-input"
          maxlength="100"
          placeholder="搜索姓名或手机号"
          confirm-type="search"
          @confirm="loadData"
        />
        <view class="toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" @click="loadData">刷新列表</button>
          <button class="toolbar-button toolbar-button-secondary action-button" @click="resetFilters">清空搜索</button>
        </view>
      </view>

      <view v-if="loading" class="card empty-state">正在加载律师列表...</view>

      <template v-else>
        <view class="card">
          <text class="section-title">待审批成员</text>
          <view v-if="!filteredPendingUsers.length" class="empty-state">当前没有待审批成员。</view>
          <view v-for="item in filteredPendingUsers" :key="item.id" class="member-card">
            <text class="list-card-title">{{ item.real_name }}</text>
            <text class="list-card-subtitle">{{ item.phone }}</text>
            <text class="meta">角色：{{ item.role_text }}</text>
            <text class="meta">状态：{{ item.status_text }}</text>
            <view class="toolbar card-toolbar">
              <button class="toolbar-button toolbar-button-secondary action-button" @click="openLawyerDetail(item, 'pending')">查看详情</button>
              <button class="toolbar-button toolbar-button-primary action-button" :loading="approveId === item.id" @click="approveUser(item)">审批通过</button>
              <button class="toolbar-button toolbar-button-secondary action-button" :loading="rejectId === item.id" @click="rejectUser(item)">拒绝</button>
            </view>
          </view>
        </view>

        <view class="card">
          <text class="section-title">机构律师</text>
          <view v-if="!filteredLawyers.length" class="empty-state">当前没有匹配的律师账号。</view>
          <view v-for="item in filteredLawyers" :key="item.id" class="member-card">
            <text class="list-card-title">{{ item.real_name }}</text>
            <text class="list-card-subtitle">{{ item.phone }}</text>
            <text class="meta">角色：{{ item.role_text }}</text>
            <text class="meta">状态：{{ item.status_text }}</text>
            <view class="toolbar card-toolbar">
              <button class="toolbar-button toolbar-button-secondary action-button" @click="openLawyerDetail(item, 'active')">查看详情</button>
              <button
                class="toolbar-button toolbar-button-primary action-button"
                :loading="toggleId === item.id"
                @click="toggleStatus(item)"
              >
                {{ item.toggle_text }}
              </button>
            </view>
          </view>
        </view>
      </template>
    </template>

    <template v-else>
      <view v-if="loading && !selectedUser" class="card empty-state">正在加载律师详情...</view>

      <template v-else-if="selectedUser">
        <view class="card">
          <text class="section-title">{{ selectedUser.real_name }}</text>
          <text class="list-card-subtitle">{{ selectedUser.phone }}</text>
          <text class="meta">角色：{{ selectedUser.role_text }}</text>
          <text class="meta">状态：{{ selectedUser.status_text }}</text>
          <text class="meta">租户 ID：{{ selectedUser.tenant_id }}</text>
          <text class="meta">成员 ID：{{ selectedUser.id }}</text>
          <view class="toolbar card-toolbar">
            <button class="toolbar-button toolbar-button-secondary action-button" @click="backToList">返回列表</button>
            <button
              v-if="selectedScope === 'pending'"
              class="toolbar-button toolbar-button-primary action-button"
              :loading="approveId === selectedUser.id"
              @click="approveUser(selectedUser)"
            >
              审批通过
            </button>
            <button
              v-if="selectedScope === 'pending'"
              class="toolbar-button toolbar-button-secondary action-button"
              :loading="rejectId === selectedUser.id"
              @click="rejectUser(selectedUser)"
            >
              拒绝申请
            </button>
            <button
              v-if="selectedScope !== 'pending'"
              class="toolbar-button toolbar-button-primary action-button"
              :loading="toggleId === selectedUser.id"
              @click="toggleStatus(selectedUser)"
            >
              {{ selectedUser.toggle_text }}
            </button>
          </view>
        </view>

        <view class="card">
          <text class="section-title">管理说明</text>
          <text class="meta">待审批成员只允许“通过”或“拒绝”；已启用成员支持停用，已停用成员支持重新启用。</text>
          <text class="meta">邀请注册仍通过统一登录页完成，审批后即可在网页端与小程序端共用同一账号登录。</text>
        </view>
      </template>

      <view v-else class="card empty-state">
        未找到该律师账号，可能已被审批或移除。
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-secondary action-button" @click="backToList">返回列表</button>
        </view>
      </view>
    </template>

    <workspace-tab-bar current-key="lawyers" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { formatRole } from "../../common/display";
import { del, get, patch, post } from "../../common/http";
import { friendlyError, showFormError } from "../../common/form";
import { buildLoginPageUrl, buildWorkspaceLawyerDetailUrl, getWorkspaceModuleUrl } from "../../common/role-routing";
import { ensureWorkspaceAccess } from "../../common/workspace";

function statusText(status) {
  const normalized = Number(status);
  if (normalized === 1) {
    return "已启用";
  }
  if (normalized === 2) {
    return "已停用";
  }
  if (normalized === 3) {
    return "已拒绝";
  }
  return "待审批";
}

function toggleText(status) {
  return Number(status) === 1 ? "停用账号" : "启用账号";
}

function normalizeMember(item, scope) {
  return {
    ...item,
    scope,
    role_text: formatRole(item.role),
    status_text: statusText(item.status),
    toggle_text: toggleText(item.status),
  };
}

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      loading: false,
      inviteLoading: false,
      detailId: 0,
      detailScope: "",
      keyword: "",
      inviteToken: "",
      invitePath: "",
      lawyers: [],
      pendingUsers: [],
      approveId: 0,
      rejectId: 0,
      toggleId: 0,
    };
  },
  computed: {
    isDetailMode() {
      return Boolean(this.detailId);
    },
    normalizedKeyword() {
      return String(this.keyword || "").trim().toLowerCase();
    },
    filteredLawyers() {
      if (!this.normalizedKeyword) {
        return this.lawyers;
      }
      return this.lawyers.filter((item) => {
        return item.real_name.toLowerCase().includes(this.normalizedKeyword) || item.phone.includes(this.normalizedKeyword);
      });
    },
    filteredPendingUsers() {
      if (!this.normalizedKeyword) {
        return this.pendingUsers;
      }
      return this.pendingUsers.filter((item) => {
        return item.real_name.toLowerCase().includes(this.normalizedKeyword) || item.phone.includes(this.normalizedKeyword);
      });
    },
    selectedUser() {
      const source = this.detailScope === "pending" ? this.pendingUsers : this.lawyers;
      return source.find((item) => Number(item.id) === Number(this.detailId)) || null;
    },
    selectedScope() {
      if (this.detailScope) {
        return this.detailScope;
      }
      if (this.pendingUsers.some((item) => Number(item.id) === Number(this.detailId))) {
        return "pending";
      }
      return "active";
    },
  },
  onLoad(options) {
    const lawyerId = Number(options.id || 0);
    this.detailId = Number.isNaN(lawyerId) ? 0 : lawyerId;
    this.detailScope = String(options.scope || "");
  },
  onShow() {
    const user = ensureWorkspaceAccess({ adminOnly: true });
    if (!user) {
      return;
    }
    this.loadData();
  },
  methods: {
    async loadData() {
      this.loading = true;
      try {
        const [lawyers, pendingUsers] = await Promise.all([
          get("/users/lawyers"),
          get("/users/pending"),
        ]);
        this.lawyers = Array.isArray(lawyers) ? lawyers.map((item) => normalizeMember(item, "active")) : [];
        this.pendingUsers = Array.isArray(pendingUsers) ? pendingUsers.map((item) => normalizeMember(item, "pending")) : [];
      } catch (error) {
        showFormError(friendlyError(error, "加载律师管理数据失败"));
      } finally {
        this.loading = false;
      }
    },
    async generateInvite() {
      this.inviteLoading = true;
      try {
        const result = await post("/users/invite-lawyer");
        this.inviteToken = result.token || "";
        this.invitePath = this.inviteToken ? buildLoginPageUrl(this.inviteToken, "lawyer-invite") : "";
        if (this.invitePath) {
          uni.showToast({ title: "邀请码已生成", icon: "success" });
        }
      } catch (error) {
        showFormError(friendlyError(error, "生成邀请码失败"));
      } finally {
        this.inviteLoading = false;
      }
    },
    copyInvite() {
      if (!this.invitePath) {
        showFormError("请先生成邀请码");
        return;
      }
      uni.setClipboardData({
        data: this.invitePath,
        success: () => {
          uni.showToast({ title: "路径已复制", icon: "success" });
        },
      });
    },
    resetFilters() {
      this.keyword = "";
    },
    openLawyerDetail(item, scope) {
      uni.navigateTo({ url: buildWorkspaceLawyerDetailUrl(item.id, scope) });
    },
    backToList() {
      if (getCurrentPages().length > 1) {
        uni.navigateBack({ delta: 1 });
        return;
      }
      uni.redirectTo({ url: getWorkspaceModuleUrl("lawyers") });
    },
    async approveUser(item) {
      this.approveId = item.id;
      try {
        await patch(`/users/${item.id}/approve`);
        uni.showToast({ title: "已审批通过", icon: "success" });
        await this.loadData();
        if (this.isDetailMode && Number(this.detailId) === Number(item.id)) {
          this.detailScope = "active";
        }
      } catch (error) {
        showFormError(friendlyError(error, "审批失败"));
      } finally {
        this.approveId = 0;
      }
    },
    async rejectUser(item) {
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "确认拒绝",
          content: "拒绝后该待审批账号会被移除，是否继续？",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
      if (!confirmed) {
        return;
      }

      this.rejectId = item.id;
      try {
        await del(`/users/${item.id}/reject`);
        uni.showToast({ title: "已拒绝申请", icon: "success" });
        await this.loadData();
        if (this.isDetailMode && Number(this.detailId) === Number(item.id)) {
          this.backToList();
        }
      } catch (error) {
        showFormError(friendlyError(error, "拒绝申请失败"));
      } finally {
        this.rejectId = 0;
      }
    },
    async toggleStatus(item) {
      const nextStatus = Number(item.status) === 1 ? 2 : 1;
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "确认操作",
          content: nextStatus === 2 ? "停用后该账号将无法登录，是否继续？" : "确认重新启用该账号吗？",
          success: (res) => resolve(Boolean(res.confirm)),
          fail: () => resolve(false),
        });
      });
      if (!confirmed) {
        return;
      }

      this.toggleId = item.id;
      try {
        await patch(`/users/${item.id}/status`, { status: nextStatus });
        uni.showToast({ title: nextStatus === 2 ? "已停用" : "已启用", icon: "success" });
        await this.loadData();
      } catch (error) {
        showFormError(friendlyError(error, "更新账号状态失败"));
      } finally {
        this.toggleId = 0;
      }
    },
  },
};
</script>

<style scoped>
.search-input {
  margin-bottom: 18rpx;
}

.card-toolbar {
  margin-top: 18rpx;
}

.invite-box {
  margin-top: 18rpx;
  padding: 20rpx;
  border-radius: 20rpx;
  background: #eff6ff;
}

.member-card {
  padding: 24rpx 0;
  border-top: 1rpx solid #e2e8f0;
}

.member-card:first-of-type {
  border-top: 0;
  padding-top: 8rpx;
}

.action-button {
  width: 100%;
}
</style>
