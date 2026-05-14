<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="hero-kicker">我的</text>
      <text class="page-hero-title">账号与工作空间</text>
      <text class="page-hero-desc">查看当前登录账号信息，并在这里统一退出登录。</text>
    </view>

    <view class="card">
      <text class="section-title">账号信息</text>
      <text class="meta">姓名：{{ displayName }}</text>
      <text class="meta">手机号：{{ displayPhone }}</text>
      <text class="meta">角色：{{ displayRole }}</text>
      <text class="meta">状态：{{ displayStatus }}</text>
    </view>

    <view class="card">
      <text class="section-title">工作空间</text>
      <text class="meta">名称：{{ tenantName }}</text>
      <text class="meta">类型：{{ tenantType }}</text>
      <text class="meta">租户编码：{{ tenantCode }}</text>
    </view>

    <view class="card">
      <text class="section-title">快捷操作</text>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-secondary action-button" @click="goHome">返回首页</button>
        <button class="toolbar-button toolbar-button-primary action-button" :loading="loading" @click="refreshProfile">
          刷新信息
        </button>
      </view>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-secondary action-button danger-button" @click="handleLogout">
          退出登录
        </button>
      </view>
    </view>

    <client-tab-bar v-if="isClient" current-key="my" />
    <workspace-tab-bar v-else current-key="my" />
  </view>
</template>

<script>
import ClientTabBar from "../../components/ClientTabBar.vue";
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { clearSession, setUserInfo } from "../../features/auth/auth";
import { formatRole, formatTenantType, formatText } from "../../shared/lib/display";
import { friendlyError, showFormError } from "../../shared/lib/form";
import { get, logoutByServer } from "../../shared/api/http";
import { getCurrentUser, logoutAndRedirect, redirectByRole, requireLogin } from "../../features/auth/session";

export default {
  components: {
    ClientTabBar,
    WorkspaceTabBar,
  },
  data() {
    return {
      loading: false,
      user: null,
      tenant: null,
    };
  },
  computed: {
    isClient() {
      return this.user?.role === "client";
    },
    displayName() {
      return formatText(this.user?.real_name, "-");
    },
    displayPhone() {
      return formatText(this.user?.phone, "-");
    },
    displayRole() {
      return formatRole(this.user?.role || "");
    },
    displayStatus() {
      return Number(this.user?.status) === 1 ? "已启用" : "待审批";
    },
    tenantName() {
      return formatText(this.tenant?.name, "未分配");
    },
    tenantType() {
      return formatTenantType(this.tenant?.type || "");
    },
    tenantCode() {
      return formatText(this.tenant?.tenant_code, "-");
    },
  },
  onShow() {
    if (!requireLogin()) {
      return;
    }
    this.user = getCurrentUser();
    this.refreshProfile();
  },
  methods: {
    async refreshProfile() {
      this.loading = true;
      try {
        const profile = await get("/users/me");
        this.user = profile || getCurrentUser();
        try {
          this.tenant = await get("/tenants/current");
          this.user = {
            ...this.user,
            tenant_type: this.tenant?.type || this.user?.tenant_type || "",
          };
        } catch {
          this.tenant = null;
        }
        setUserInfo(this.user);
      } catch (error) {
        // 401 由 http 层的 handleUnauthorized 自动处理（重定向到登录页）
        // 只对非 401 错误显示 toast
        const status = error?.response?.status || error?.statusCode;
        if (status !== 401) {
          showFormError(friendlyError(error, "加载我的信息失败"));
        }
      } finally {
        this.loading = false;
      }
    },
    async goHome() {
      try {
        await redirectByRole(this.user || getCurrentUser());
      } catch {
        showFormError("跳转失败，请重试");
      }
    },
    async handleLogout() {
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "退出登录",
          content: "确认退出当前账号吗？",
          success: (result) => resolve(Boolean(result.confirm)),
          fail: () => resolve(false),
        });
      });

      if (!confirmed) {
        return;
      }

      try {
        await logoutAndRedirect();
      } catch {
        try {
          await logoutByServer();
        } catch {
          // ignore
        }
        clearSession();
        uni.reLaunch({ url: "/pages/login/index" });
      }
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

.danger-button {
  color: #d70015;
}
</style>

