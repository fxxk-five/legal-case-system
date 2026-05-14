<template>
  <view class="page-container fade-in">
    <view class="card hero-card">
      <text class="hero-kicker">安全校验</text>
      <text class="hero-title">首次登录请先修改密码</text>
      <text class="hero-desc">
        为了保护账号安全，系统要求你先设置新密码。修改完成后会自动重新建立会话，再进入对应工作台。</text>
      <text class="hero-meta">当前账号：{{ maskedPhone }}</text>
    </view>

    <view class="card">
      <text class="section-title">设置新密码</text>
      <text class="meta">密码至少 8 位；建议同时包含字母和数字。</text>

      <input
        v-model="form.newPassword"
        class="input field-gap"
        maxlength="128"
        password
        placeholder="请输入新密码"
      />
      <input
        v-model="form.confirmPassword"
        class="input field-gap"
        maxlength="128"
        password
        placeholder="请再次输入新密码"
      />

      <button
        class="toolbar-button toolbar-button-primary primary-button field-gap"
        :loading="submitting"
        :disabled="submitting"
        @click="submitReset"
      >
        确认修改并重新登录</button>
    </view>

    <view v-if="statusMessage" class="card">
      <text class="section-title">当前状态</text>
      <view class="status-panel" :class="statusPanelClass">
        <text class="status-title">{{ statusTitle }}</text>
        <text class="status-desc">{{ statusMessage }}</text>
      </view>
      <button
        v-if="showBackToLogin"
        class="toolbar-button toolbar-button-secondary primary-button field-gap"
        @click="goLogin"
      >
        返回登录</button>
    </view>
  </view>
</template>

<script>
import { clearSession, getUserInfo, setAccessToken, setRefreshToken, setUserInfo } from "../../features/auth/auth";
import { changePassword, get, loginByPassword, logoutByServer } from "../../shared/api/http";
import { buildLoginPageUrl } from "../../features/auth/role-routing";
import { redirectByRole, requireLogin } from "../../features/auth/session";
import { friendlyError, showFormError, validatePassword } from "../../shared/lib/form";

export default {
  data() {
    return {
      form: {
        newPassword: "",
        confirmPassword: "",
      },
      submitting: false,
      statusTitle: "",
      statusMessage: "",
      statusTone: "info",
      showBackToLogin: false,
    };
  },
  computed: {
    currentUser() {
      return getUserInfo();
    },
    maskedPhone() {
      const phone = String(this.currentUser?.phone || "");
      if (!phone) {
        return "-";
      }
      if (phone.length < 7) {
        return phone;
      }
      return `${phone.slice(0, 3)}****${phone.slice(-4)}`;
    },
    statusPanelClass() {
      return `status-${this.statusTone}`;
    },
  },
  onShow() {
    this.ensureResetRequired();
  },
  methods: {
    setStatus(title, message, tone = "info") {
      this.statusTitle = title || "";
      this.statusMessage = message || "";
      this.statusTone = tone || "info";
    },
    clearStatus() {
      this.statusTitle = "";
      this.statusMessage = "";
      this.statusTone = "info";
    },
    async ensureResetRequired() {
      if (!requireLogin()) {
        return false;
      }

      const user = getUserInfo();
      if (!user) {
        uni.reLaunch({ url: buildLoginPageUrl() });
        return false;
      }

      if (!user.must_reset_password) {
        await redirectByRole(user);
        return false;
      }

      return true;
    },
    async resolveTenantCodeForRelogin(user) {
      if (!user || user.role === "client") {
        return "";
      }
      try {
        const tenant = await get("/tenants/current");
        return String(tenant?.tenant_code || "").trim();
      } catch {
        return "";
      }
    },
    async rebuildSessionAfterPasswordReset({ phone, newPassword, tenantCode }) {
      await logoutByServer();
      const payload = await loginByPassword({
        phone,
        password: newPassword,
        tenant_code: tenantCode || null,
      });

      setAccessToken(payload?.access_token || "");
      setRefreshToken(payload?.refresh_token || "");

      const profile = await get("/users/me");
      if (!profile) {
        throw { message: "未获取到用户信息，请重新登录。" };
      }

      let nextUser = { ...(profile || {}) };
      if (nextUser.role !== "client") {
        try {
          const tenant = await get("/tenants/current");
          if (tenant?.type) {
            nextUser = {
              ...nextUser,
              tenant_type: tenant.type,
            };
          }
        } catch {
          // Ignore tenant enrichment failures.
        }
      }
      setUserInfo(nextUser);
      return nextUser;
    },
    async submitReset() {
      const valid = await this.ensureResetRequired();
      if (!valid) {
        return;
      }

      const passwordError = validatePassword(this.form.newPassword, "新密码");
      if (passwordError) {
        showFormError(passwordError);
        this.setStatus("校验失败", passwordError, "warning");
        return;
      }
      if (this.form.newPassword !== this.form.confirmPassword) {
        const message = "两次输入的新密码不一致。";
        showFormError(message);
        this.setStatus("校验失败", message, "warning");
        return;
      }

      const user = getUserInfo();
      const phone = String(user?.phone || "").trim();
      if (!phone) {
        const message = "当前账号手机号缺失，请重新登录后再试。";
        showFormError(message);
        this.setStatus("提交失败", message, "error");
        this.showBackToLogin = true;
        return;
      }

      this.submitting = true;
      this.showBackToLogin = false;
      this.clearStatus();

      try {
        await changePassword({
          new_password: this.form.newPassword,
        });

        const tenantCode = await this.resolveTenantCodeForRelogin(user);
        await this.rebuildSessionAfterPasswordReset({
          phone,
          newPassword: this.form.newPassword,
          tenantCode,
        });

        this.setStatus("修改成功", "密码已更新，正在进入工作台。", "success");
        await redirectByRole(getUserInfo());
      } catch (error) {
        const message = friendlyError(error, "密码修改失败，请稍后重试。");
        this.setStatus("修改失败", message, "error");
        showFormError(message);
        if (!requireLogin()) {
          this.showBackToLogin = true;
        }
      } finally {
        this.submitting = false;
      }
    },
    goLogin() {
      clearSession();
      uni.reLaunch({ url: buildLoginPageUrl() });
    },
  },
};
</script>

<style scoped>
.hero-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(245, 245, 247, 0.92));
  color: #1d1d1f;
}

.hero-kicker {
  display: block;
  font-size: 22rpx;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: #6e6e73;
}

.hero-title {
  display: block;
  margin-top: 10rpx;
  font-size: 52rpx;
  font-weight: 700;
  line-height: 1.1;
}

.hero-desc {
  display: block;
  margin-top: 12rpx;
  line-height: 1.7;
  color: #6e6e73;
}

.hero-meta {
  display: block;
  margin-top: 16rpx;
  color: #3c3c43;
  font-size: 24rpx;
}

.field-gap {
  margin-top: 18rpx;
}

.primary-button {
  width: 100%;
}

.status-panel {
  padding: 24rpx;
  border-radius: 24rpx;
}

.status-info {
  background: rgba(0, 113, 227, 0.08);
  color: #0071e3;
}

.status-success {
  background: rgba(52, 199, 89, 0.12);
  color: #248a3d;
}

.status-warning {
  background: rgba(255, 159, 10, 0.12);
  color: #b86e00;
}

.status-error {
  background: rgba(255, 59, 48, 0.12);
  color: #c9342c;
}

.status-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
}

.status-desc {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>

