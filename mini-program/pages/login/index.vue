<template>
  <view class="page-container fade-in">
    <view class="card hero-card">
      <text class="hero-kicker">{{ textMap.login }}</text>
      <text class="hero-title">{{ textMap.wechatLogin }}</text>
      <text class="hero-desc">{{ heroDescription }}</text>
    </view>

    <view v-if="isClientInviteMode" class="card">
      <text class="section-title">{{ textMap.caseInvite }}</text>
      <text class="meta">{{ textMap.caseInviteDesc }}</text>
      <text class="meta token-text">{{ textMap.clientScene }}</text>
    </view>

    <view v-if="isLawyerInviteMode" class="card">
      <text class="section-title">{{ textMap.lawyerInvite }}</text>
      <text class="meta">{{ textMap.lawyerInviteDesc }}</text>
      <text class="meta token-text">{{ textMap.lawyerScene }}</text>
      <button class="toolbar-button toolbar-button-secondary helper-button" @click="goStandardLogin">
        {{ textMap.standardLogin }}
      </button>
    </view>

    <view v-if="isWebLoginMode" class="card">
      <text class="section-title">{{ textMap.webConfirm }}</text>
      <text class="meta">{{ textMap.webConfirmDesc }}</text>
      <text class="meta token-text">{{ textMap.ticketPrefix }}{{ webLoginTicket }}</text>
    </view>

    <view class="card">
      <text class="section-title">{{ textMap.quickLogin }}</text>
      <text class="meta">{{ textMap.quickLoginDesc }}</text>
      <view class="toolbar dev-login-toolbar">
        <button class="toolbar-button toolbar-button-primary dev-login-button" @click="devLogin('tenant_admin')">
          {{ textMap.adminEnter }}
        </button>
        <button class="toolbar-button toolbar-button-secondary dev-login-button" @click="devLogin('lawyer')">
          {{ textMap.lawyerEnter }}
        </button>
        <button class="toolbar-button toolbar-button-secondary dev-login-button" @click="devLogin('client')">
          {{ textMap.clientEnter }}
        </button>
      </view>
    </view>

    <view class="card">
      <text class="section-title">{{ textMap.formalLogin }}</text>
      <text class="meta">{{ directLoginDescription }}</text>
      <input
        v-if="showTenantCodeInput"
        v-model="tenantCode"
        class="input field-gap"
        maxlength="50"
        :placeholder="textMap.tenantPlaceholder"
      />
      <button class="toolbar-button toolbar-button-primary primary-button" :loading="loginSubmitting" :disabled="busy" @click="startWechatLogin">
        {{ textMap.wechatAuthLogin }}
      </button>
    </view>

    <view v-if="awaitingPhoneAuth" class="card">
      <text class="section-title">{{ textMap.phoneAuth }}</text>
      <text class="meta">{{ textMap.phoneAuthDesc }}</text>
      <button
        class="toolbar-button toolbar-button-primary primary-button"
        open-type="getPhoneNumber"
        :loading="phoneSubmitting"
        :disabled="busy"
        @getphonenumber="handleGetPhoneNumber"
      >
        {{ textMap.continueAuth }}
      </button>
      <button class="toolbar-button toolbar-button-secondary helper-button" :disabled="busy" @click="restartWechatLogin">
        {{ textMap.retryGet }}
      </button>
    </view>

    <view v-if="statusMessage" class="card">
      <text class="section-title">{{ textMap.currentStatus }}</text>
      <view class="status-panel" :class="statusPanelClass">
        <text class="status-title">{{ statusTitle }}</text>
        <text class="status-desc">{{ statusMessage }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import { get, post, wxMiniLogin, wxMiniPhoneLogin } from "../../common/http";
import { clearSession, setAccessToken, setRefreshToken, setUserInfo, setWechatOpenid } from "../../common/auth";
import { buildLoginPageUrl } from "../../common/role-routing";
import { getCurrentUser, redirectByRole } from "../../common/session";
import { friendlyError, showFormError, validateTenantCode } from "../../common/form";

const CLIENT_SCENE = "client-case";
const LAWYER_INVITE_SCENE = "lawyer-invite";
const WEB_LOGIN_SCENE = "web-login";
const WEB_LOGIN_SCENE_PREFIX = "web-login:";

function buildDevUser(role) {
  if (role === "client") {
    return {
      id: 10001,
      role: "client",
      real_name: "\u6d4b\u8bd5\u5f53\u4e8b\u4eba",
      phone: "13800000001",
      tenant_type: "personal",
      status: 1,
    };
  }
  if (role === "tenant_admin") {
    return {
      id: 20001,
      role: "tenant_admin",
      real_name: "\u6d4b\u8bd5\u7ba1\u7406\u5458",
      phone: "13800000002",
      tenant_type: "organization",
      is_tenant_admin: true,
      status: 1,
    };
  }
  return {
    id: 20002,
    role: "lawyer",
    real_name: "\u6d4b\u8bd5\u5f8b\u5e08",
    phone: "13800000003",
    tenant_type: "organization",
    is_tenant_admin: false,
    status: 1,
  };
}

export default {
  data() {
    return {
      textMap: {
        login: "\u767b\u5f55",
        wechatLogin: "\u5fae\u4fe1\u767b\u5f55",
        caseInvite: "\u6848\u4ef6\u9080\u8bf7",
        caseInviteDesc: "\u767b\u5f55\u540e\u81ea\u52a8\u7ed1\u5b9a\u6848\u4ef6\u3002",
        clientScene: "\u573a\u666f\uff1a\u6848\u4ef6\u9080\u8bf7\u5165\u53e3",
        lawyerInvite: "\u5f8b\u5e08\u9080\u8bf7",
        lawyerInviteDesc: "\u767b\u5f55\u540e\u7ee7\u7eed\u52a0\u5165\u6d41\u7a0b\u3002",
        lawyerScene: "\u573a\u666f\uff1a\u5f8b\u5e08\u9080\u8bf7\u5165\u53e3",
        standardLogin: "\u666e\u901a\u767b\u5f55",
        webConfirm: "\u7f51\u9875\u786e\u8ba4",
        webConfirmDesc: "\u6388\u6743\u540e\u540c\u6b65\u5230\u7535\u8111\u7aef\u3002",
        ticketPrefix: "\u7968\u636e\uff1a",
        quickLogin: "\u5feb\u6377\u767b\u5f55",
        quickLoginDesc: "\u5f00\u53d1\u9636\u6bb5\u53ef\u76f4\u63a5\u8fdb\u5165\uff0c\u6b63\u5f0f\u90e8\u7f72\u65f6\u518d\u5207\u56de\u5fae\u4fe1\u6388\u6743\u3002",
        adminEnter: "\u7ba1\u7406\u5458\u8fdb\u5165",
        lawyerEnter: "\u5f8b\u5e08\u8fdb\u5165",
        clientEnter: "\u5f53\u4e8b\u4eba\u8fdb\u5165",
        formalLogin: "\u6b63\u5f0f\u767b\u5f55",
        tenantPlaceholder: "\u53ef\u9009\uff1a\u79df\u6237\u7f16\u7801",
        wechatAuthLogin: "\u5fae\u4fe1\u6388\u6743\u767b\u5f55",
        phoneAuth: "\u624b\u673a\u53f7\u6388\u6743",
        phoneAuthDesc: "\u7528\u4e8e\u786e\u8ba4\u8eab\u4efd\u5e76\u5b8c\u6210\u7ed1\u5b9a\u3002",
        continueAuth: "\u7ee7\u7eed\u6388\u6743",
        retryGet: "\u91cd\u65b0\u83b7\u53d6",
        currentStatus: "\u5f53\u524d\u72b6\u6001",
      },
      scene: "",
      lawyerInviteToken: "",
      clientInviteToken: "",
      webLoginTicket: "",
      tenantCode: "",
      wxSessionTicket: "",
      wechatOpenid: "",
      loginSubmitting: false,
      phoneSubmitting: false,
      statusTitle: "",
      statusMessage: "",
      statusTone: "info",
    };
  },
  computed: {
    isClientInviteMode() {
      return this.scene === CLIENT_SCENE && !!this.clientInviteToken;
    },
    isLawyerInviteMode() {
      return this.scene === LAWYER_INVITE_SCENE && !!this.lawyerInviteToken;
    },
    isWebLoginMode() {
      return this.scene === WEB_LOGIN_SCENE && !!this.webLoginTicket;
    },
    showTenantCodeInput() {
      return !this.isClientInviteMode && !this.isLawyerInviteMode;
    },
    awaitingPhoneAuth() {
      return !!this.wxSessionTicket;
    },
    busy() {
      return this.loginSubmitting || this.phoneSubmitting;
    },
    heroDescription() {
      if (this.isWebLoginMode) {
        return "\u8bf7\u786e\u8ba4\u7535\u8111\u7aef\u767b\u5f55\u3002";
      }
      if (this.isClientInviteMode) {
        return "\u767b\u5f55\u540e\u76f4\u63a5\u8fdb\u5165\u6848\u4ef6\u3002";
      }
      if (this.isLawyerInviteMode) {
        return "\u767b\u5f55\u540e\u7ee7\u7eed\u52a0\u5165\u5de5\u4f5c\u533a\u3002";
      }
      return "\u5f8b\u5e08\u4e0e\u5f53\u4e8b\u4eba\u7edf\u4e00\u767b\u5f55\u5165\u53e3\u3002";
    },
    directLoginDescription() {
      if (this.isClientInviteMode) {
        return "\u7cfb\u7edf\u4f1a\u81ea\u52a8\u8bc6\u522b\u6848\u4ef6\u9080\u8bf7\u3002";
      }
      if (this.isLawyerInviteMode) {
        return "\u7cfb\u7edf\u4f1a\u81ea\u52a8\u8bc6\u522b\u673a\u6784\u9080\u8bf7\u3002";
      }
      if (this.isWebLoginMode) {
        return "\u5f53\u524d\u4f1a\u8bdd\u5c06\u540c\u6b65\u5230\u7f51\u9875\u7aef\u3002";
      }
      return "\u5982\u540c\u624b\u673a\u53f7\u5b58\u5728\u591a\u4e2a\u79df\u6237\uff0c\u53ef\u586b\u5199\u79df\u6237\u7f16\u7801\u3002";
    },
    statusPanelClass() {
      return `status-${this.statusTone}`;
    },
  },
  onLoad(options) {
    this.applyEntryOptions(options);
    const currentUser = getCurrentUser();
    if (!currentUser) {
      return;
    }
    if (this.isWebLoginMode) {
      this.confirmWebLoginForCurrentUser(currentUser);
      return;
    }
    redirectByRole(currentUser);
  },
  methods: {
    applyEntryOptions(options = {}) {
      const rawScene = decodeURIComponent(String(options.scene || "").trim());
      const queryToken = String(options.token || "").trim();
      const queryTicket = String(options.ticket || "").trim();

      this.scene = "";
      this.clientInviteToken = "";
      this.lawyerInviteToken = "";
      this.webLoginTicket = "";

      if (rawScene.startsWith(WEB_LOGIN_SCENE_PREFIX)) {
        this.scene = WEB_LOGIN_SCENE;
        this.webLoginTicket = rawScene.slice(WEB_LOGIN_SCENE_PREFIX.length).trim();
        return;
      }
      if (rawScene === CLIENT_SCENE) {
        this.scene = CLIENT_SCENE;
        this.clientInviteToken = queryToken;
        return;
      }
      if (rawScene === LAWYER_INVITE_SCENE) {
        this.scene = LAWYER_INVITE_SCENE;
        this.lawyerInviteToken = queryToken;
        return;
      }
      if (rawScene === WEB_LOGIN_SCENE) {
        this.scene = WEB_LOGIN_SCENE;
        this.webLoginTicket = queryTicket || queryToken;
        return;
      }
      if (queryToken) {
        this.scene = LAWYER_INVITE_SCENE;
        this.lawyerInviteToken = queryToken;
      }
    },
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
    async devLogin(role) {
      const user = buildDevUser(role);
      setAccessToken(`dev-token-${role}`);
      setRefreshToken("");
      setWechatOpenid(`dev-openid-${role}`);
      setUserInfo(user);
      this.setStatus(
        "\u5f00\u53d1\u767b\u5f55\u6210\u529f",
        `\u5df2\u4f5c\u4e3a${user.real_name}\u8fdb\u5165\u3002\u6b63\u5f0f\u90e8\u7f72\u524d\u8bf7\u5207\u56de\u5fae\u4fe1\u6388\u6743\u767b\u5f55\u3002`,
        "success"
      );
      await redirectByRole(user);
    },
    async requestWechatLoginCode() {
      return new Promise((resolve, reject) => {
        uni.login({
          provider: "weixin",
          success: (result) => {
            const code = result && result.code ? String(result.code) : "";
            if (!code) {
              reject({ message: "\u672a\u83b7\u53d6\u5230\u6709\u6548\u767b\u5f55\u51ed\u8bc1\uff0c\u8bf7\u91cd\u8bd5\u3002" });
              return;
            }
            resolve(code);
          },
          fail: (error) => reject(error),
        });
      });
    },
    async fetchCurrentUser() {
      return get("/users/me");
    },
    async enrichWorkspaceUser(user) {
      if (!user || user.role === "client") {
        return user;
      }
      try {
        const tenant = await get("/tenants/current");
        if (!tenant || !tenant.type) {
          return user;
        }
        return { ...user, tenant_type: tenant.type };
      } catch {
        return user;
      }
    },
    async confirmWebLoginForCurrentUser(user) {
      if (!this.webLoginTicket) {
        return;
      }
      try {
        await post(`/auth/web-wechat-login/${encodeURIComponent(this.webLoginTicket)}/confirm`);
        this.setStatus("\u786e\u8ba4\u6210\u529f", "\u7535\u8111\u7aef\u4f1a\u8bdd\u5df2\u5c31\u7eea\u3002", "success");
        setTimeout(() => {
          redirectByRole(user);
        }, 300);
      } catch (error) {
        this.setStatus("\u786e\u8ba4\u5931\u8d25", friendlyError(error, "\u5f53\u524d\u8d26\u53f7\u65e0\u6cd5\u786e\u8ba4\u7f51\u9875\u767b\u5f55\u3002"), "warning");
        showFormError(friendlyError(error, "\u5f53\u524d\u8d26\u53f7\u65e0\u6cd5\u786e\u8ba4\u7f51\u9875\u767b\u5f55\u3002"));
      }
    },
    async finishLogin(payload) {
      const accessToken = payload && payload.access_token ? payload.access_token : "";
      if (!accessToken) {
        throw { message: "\u767b\u5f55\u7ed3\u679c\u7f3a\u5c11 access_token\u3002" };
      }
      setAccessToken(accessToken);
      setRefreshToken((payload && payload.refresh_token) || "");
      setWechatOpenid((payload && payload.wechat_openid) || this.wechatOpenid || "");

      let user = payload && payload.user ? payload.user : null;
      if (!user) {
        user = await this.fetchCurrentUser();
      }
      if (!user) {
        clearSession();
        throw { message: "\u672a\u83b7\u53d6\u5230\u5f53\u524d\u7528\u6237\u4fe1\u606f\u3002" };
      }

      const enrichedUser = await this.enrichWorkspaceUser(user);
      setUserInfo(enrichedUser);
      this.wxSessionTicket = "";

      if (this.isWebLoginMode) {
        await this.confirmWebLoginForCurrentUser(enrichedUser);
        return;
      }
      this.setStatus("\u767b\u5f55\u6210\u529f", "\u6b63\u5728\u8fdb\u5165\u5de5\u4f5c\u53f0\u3002", "success");
      redirectByRole(enrichedUser);
    },
    async handleLoginResult(payload) {
      this.wechatOpenid = payload.wechat_openid || this.wechatOpenid || "";
      if (payload.need_bind_phone) {
        this.wxSessionTicket = payload.wx_session_ticket || "";
        this.setStatus("\u9700\u8981\u624b\u673a\u53f7\u6388\u6743", "\u8bf7\u7ee7\u7eed\u5b8c\u6210\u624b\u673a\u53f7\u6388\u6743\u3002", "info");
        return;
      }
      if (!payload.access_token || payload.login_state === "PENDING_APPROVAL") {
        clearSession();
        this.wxSessionTicket = "";
        this.setStatus("\u7b49\u5f85\u5ba1\u6279", "\u5f53\u524d\u8d26\u53f7\u6b63\u5728\u7b49\u5f85\u7ba1\u7406\u5458\u5ba1\u6279\u3002", "warning");
        return;
      }
      await this.finishLogin(payload);
    },
    async startWechatLogin() {
      const tenantCodeMessage = this.showTenantCodeInput ? validateTenantCode(this.tenantCode, false) : "";
      if (tenantCodeMessage) {
        showFormError(tenantCodeMessage);
        return;
      }
      this.loginSubmitting = true;
      this.wxSessionTicket = "";
      this.clearStatus();
      try {
        const code = await this.requestWechatLoginCode();
        const payload = await wxMiniLogin({ code });
        await this.handleLoginResult(payload);
      } catch (error) {
        const message = friendlyError(error, "\u5fae\u4fe1\u767b\u5f55\u5931\u8d25");
        this.setStatus("\u767b\u5f55\u5931\u8d25", message, "error");
        showFormError(message);
      } finally {
        this.loginSubmitting = false;
      }
    },
    async restartWechatLogin() {
      this.wxSessionTicket = "";
      await this.startWechatLogin();
    },
    async handleGetPhoneNumber(event) {
      if (!this.wxSessionTicket) {
        showFormError("\u8bf7\u5148\u5b8c\u6210\u5fae\u4fe1\u6388\u6743\u767b\u5f55\u3002");
        return;
      }
      const tenantCodeMessage = this.showTenantCodeInput ? validateTenantCode(this.tenantCode, false) : "";
      if (tenantCodeMessage) {
        showFormError(tenantCodeMessage);
        return;
      }
      const detail = event && event.detail ? event.detail : {};
      const phoneCode = detail && detail.code ? String(detail.code) : "";
      if (!phoneCode) {
        const message = "\u4f60\u5df2\u53d6\u6d88\u624b\u673a\u53f7\u6388\u6743\u3002";
        this.setStatus("\u6388\u6743\u5df2\u53d6\u6d88", message, "warning");
        showFormError(message);
        return;
      }
      this.phoneSubmitting = true;
      try {
        const payload = await wxMiniPhoneLogin({
          phone_code: phoneCode,
          wx_session_ticket: this.wxSessionTicket,
          tenant_code: this.showTenantCodeInput ? this.tenantCode.trim() || null : null,
          case_invite_token: this.isClientInviteMode ? this.clientInviteToken : null,
          lawyer_invite_token: this.isLawyerInviteMode ? this.lawyerInviteToken : null,
        });
        await this.handleLoginResult(payload);
      } catch (error) {
        const message = friendlyError(error, "\u624b\u673a\u53f7\u6388\u6743\u5931\u8d25");
        this.setStatus("\u767b\u5f55\u5931\u8d25", message, "error");
        showFormError(message);
      } finally {
        this.phoneSubmitting = false;
      }
    },
    goStandardLogin() {
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

.hero-title {
  display: block;
  font-size: 52rpx;
  font-weight: 700;
  line-height: 1.1;
}

.hero-desc {
  display: block;
  margin-top: 12rpx;
  line-height: 1.6;
  color: #6e6e73;
}

.field-gap {
  margin-top: 18rpx;
}

.token-text {
  margin-top: 12rpx;
}

.primary-button,
.helper-button,
.dev-login-button {
  width: 100%;
}

.helper-button {
  margin-top: 12rpx;
}

.dev-login-toolbar {
  margin-top: 18rpx;
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
