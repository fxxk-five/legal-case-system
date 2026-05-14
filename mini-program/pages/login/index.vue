<template>
  <view class="page-container fade-in">
    <view class="card hero-card">
      <text class="hero-kicker">{{ textMap.login }}</text>
      <text class="hero-title">{{ textMap.heroTitle }}</text>
      <text class="hero-desc">{{ heroDescription }}</text>
    </view>

    <view v-if="isClientInviteMode" class="card">
      <text class="section-title">{{ textMap.caseInvite }}</text>
      <text class="meta">{{ textMap.caseInviteDesc }}</text>
      <text class="meta token-text">{{ textMap.clientScene }}</text>
      <text class="meta helper-copy">{{ textMap.clientPhoneReminder }}</text>
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

    <view v-if="showMethodSwitch" class="card">
      <text class="section-title">{{ textMap.methodTitle }}</text>
      <text class="meta">{{ textMap.methodDesc }}</text>
      <view class="method-switch">
        <button
          class="method-chip"
          :class="{ 'method-chip-active': activeLoginMethod === 'wechat' }"
          @click="selectLoginMethod('wechat')"
        >
          {{ textMap.wechatMethod }}
        </button>
        <button
          class="method-chip"
          :class="{ 'method-chip-active': activeLoginMethod === 'sms' }"
          @click="selectLoginMethod('sms')"
        >
          {{ textMap.smsMethod }}
        </button>
        <button
          class="method-chip"
          :class="{ 'method-chip-active': activeLoginMethod === 'password' }"
          @click="selectLoginMethod('password')"
        >
          {{ textMap.passwordMethod }}
        </button>
      </view>
    </view>

    <view class="card">
      <text class="section-title">{{ currentMethodTitle }}</text>
      <text class="meta">{{ currentMethodDescription }}</text>

      <input
        v-if="showTenantCodeInput"
        v-model="tenantCode"
        class="input field-gap"
        maxlength="50"
        :placeholder="textMap.tenantPlaceholder"
      />

      <template v-if="activeLoginMethod === 'wechat'">
        <button
          class="toolbar-button toolbar-button-primary primary-button"
          :loading="loginSubmitting"
          :disabled="busy"
          @click="startWechatLogin"
        >
          {{ textMap.wechatAuthLogin }}
        </button>
        <text class="meta helper-copy">{{ wechatHelperText }}</text>
      </template>

      <template v-else-if="activeLoginMethod === 'sms'">
        <input
          v-model="smsForm.phone"
          class="input field-gap"
          maxlength="11"
          type="number"
          :placeholder="textMap.phonePlaceholder"
        />
        <view class="inline-action field-gap">
          <input
            v-model="smsForm.code"
            class="input inline-input"
            maxlength="6"
            type="number"
            :placeholder="textMap.smsCodePlaceholder"
          />
          <button
            class="toolbar-button toolbar-button-secondary inline-button"
            :disabled="busy || smsCooldown > 0"
            @click="sendLoginSmsCode"
          >
            {{ smsCooldown > 0 ? `${smsCooldown}s` : textMap.sendCode }}
          </button>
        </view>
        <button
          class="toolbar-button toolbar-button-primary primary-button"
          :loading="smsLoginSubmitting"
          :disabled="busy"
          @click="submitSmsLogin"
        >
          {{ textMap.smsLoginAction }}
        </button>
        <text class="meta helper-copy">{{ smsHelperText }}</text>
      </template>

      <template v-else>
        <input
          v-model="passwordForm.phone"
          class="input field-gap"
          maxlength="11"
          type="number"
          :placeholder="textMap.phonePlaceholder"
        />
        <input
          v-model="passwordForm.password"
          class="input field-gap"
          maxlength="128"
          password
          :placeholder="textMap.passwordPlaceholder"
        />
        <button
          class="toolbar-button toolbar-button-primary primary-button"
          :loading="passwordSubmitting"
          :disabled="busy"
          @click="submitPasswordLogin"
        >
          {{ textMap.passwordLoginAction }}
        </button>
        <text class="meta helper-copy">{{ passwordHelperText }}</text>
      </template>
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
import {
  get,
  post,
  loginByPassword,
  loginBySmsCode,
  fetchLoginAdvice,
  sendSmsCode,
  wxMiniLogin,
  wxMiniPhoneLogin,
} from "../../shared/api/http";
import { clearSession, setAccessToken, setRefreshToken, setUserInfo, setWechatOpenid } from "../../features/auth/auth";
import { buildLoginPageUrl } from "../../features/auth/role-routing";
import { getCurrentUser, redirectByRole } from "../../features/auth/session";
import {
  friendlyError,
  showFormError,
  validatePassword,
  validatePhone,
  validateSmsCode,
  validateTenantCode,
} from "../../shared/lib/form";

const CLIENT_SCENE = "client-case";
const LAWYER_INVITE_SCENE = "lawyer-invite";
const WEB_LOGIN_SCENE = "web-login";
const WEB_LOGIN_SCENE_PREFIX = "web-login:";

export default {
  data() {
    return {
      textMap: {
        login: "登录",
        heroTitle: "安全登录",
        caseInvite: "案件邀请",
        caseInviteDesc: "首次进入时，请优先使用案件预留手机号登录，系统会在登录后自动关联案件。",
        clientScene: "场景：案件邀请入口",
        clientPhoneReminder: "如你是首次使用，优先选“微信一键登录”或“短信验证码登录”。",
        lawyerInvite: "律师邀请",
        lawyerInviteDesc: "当前入口用于律师邀请联动，若你已有账号可继续使用微信登录。",
        lawyerScene: "场景：律师邀请入口",
        standardLogin: "返回普通登录",
        webConfirm: "网页确认",
        webConfirmDesc: "完成登录后，当前会话会同步到电脑端。",
        ticketPrefix: "票据：",
        methodTitle: "选择登录方式",
        methodDesc: "手机号是账号核心字段，微信、短信验证码和账号密码会归并到同一账号。",
        wechatMethod: "微信一键登录",
        smsMethod: "短信验证码",
        passwordMethod: "账号密码",
        tenantPlaceholder: "可选：租户编码",
        phonePlaceholder: "请输入手机号",
        smsCodePlaceholder: "请输入 6 位验证码",
        passwordPlaceholder: "请输入密码",
        wechatAuthLogin: "发起微信登录",
        smsLoginAction: "验证码登录",
        passwordLoginAction: "账号密码登录",
        phoneAuth: "手机号授权",
        phoneAuthDesc: "用于确认身份并完成微信登录绑定。",
        continueAuth: "继续授权手机号",
        retryGet: "重新获取微信凭证",
        currentStatus: "当前状态",
        sendCode: "发送验证码",
      },
      scene: "",
      lawyerInviteToken: "",
      clientInviteToken: "",
      webLoginTicket: "",
      tenantCode: "",
      wxSessionTicket: "",
      wechatOpenid: "",
      activeLoginMethod: "wechat",
      loginSubmitting: false,
      phoneSubmitting: false,
      smsSending: false,
      smsLoginSubmitting: false,
      passwordSubmitting: false,
      smsCooldown: 0,
      smsTimer: null,
      smsForm: {
        phone: "",
        code: "",
      },
      passwordForm: {
        phone: "",
        password: "",
      },
      statusTitle: "",
      statusMessage: "",
      statusTone: "info",
      loginAdvice: {
        requires_tenant_code: false,
        requires_admin_approval: false,
        recommended_entry: "web",
      },
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
    showMethodSwitch() {
      return !this.isLawyerInviteMode;
    },
    showTenantCodeInput() {
      return !this.isClientInviteMode && !this.isLawyerInviteMode;
    },
    awaitingPhoneAuth() {
      return !!this.wxSessionTicket;
    },
    busy() {
      return (
        this.loginSubmitting ||
        this.phoneSubmitting ||
        this.smsSending ||
        this.smsLoginSubmitting ||
        this.passwordSubmitting
      );
    },
    heroDescription() {
      if (this.isWebLoginMode) {
        return "登录成功后会自动确认电脑端扫码请求。";
      }
      if (this.isClientInviteMode) {
        return "律师已把你带到指定案件，请使用同一手机号完成登录。";
      }
      if (this.isLawyerInviteMode) {
        return "邀请中的律师请继续完成已有账号的微信登录。";
      }
      return "同一手机号会统一归并到一个账号，避免登录通道分裂。";
    },
    currentMethodTitle() {
      if (this.activeLoginMethod === "sms") {
        return "短信验证码登录";
      }
      if (this.activeLoginMethod === "password") {
        return "账号密码登录";
      }
      return "微信一键登录";
    },
    currentMethodDescription() {
      if (this.activeLoginMethod === "sms") {
        if (this.isClientInviteMode) {
          return "适合首次进入案件的小程序用户。验证码登录成功后，系统会直接关联案件。";
        }
        return "适合临时设备登录或忘记密码时使用。";
      }
      if (this.activeLoginMethod === "password") {
        if (this.isClientInviteMode) {
          return "适合已设置过密码的当事人账号。若首次使用，请优先改用短信或微信登录。";
        }
        return "适合已有固定账号密码的用户。";
      }
      if (this.isClientInviteMode) {
        return "系统会先确认微信身份，再通过手机号自动匹配案件账号。";
      }
      return "适合已绑定微信的用户，授权后可直接进入工作台。";
    },
    wechatHelperText() {
      if (this.isClientInviteMode) {
        return "若你是首次使用，微信授权手机号后会直接和当前案件绑定。";
      }
      if (this.isWebLoginMode) {
        return "登录完成后会自动确认电脑端扫码票据。";
      }
      return "如手机号命中多个租户，可补充租户编码后再继续。";
    },
    smsHelperText() {
      if (this.isClientInviteMode) {
        return "验证码会发送到案件预留手机号；登录成功后将直接进入你的案件。";
      }
      if (this.loginAdvice?.requires_tenant_code) {
        return "该手机号存在多个租户，本次登录需填写 tenant_code。";
      }
      return "发送后验证码 6 位有效，若手机号命中多个租户，请补充租户编码。";
    },
    passwordHelperText() {
      if (this.isClientInviteMode) {
        return "仅适用于已设置密码的账号；首次使用建议走短信验证码或微信一键登录。";
      }
      if (this.loginAdvice?.requires_tenant_code) {
        return "该手机号存在多个租户，本次登录需填写 tenant_code。";
      }
      return "账号即手机号；若手机号命中多个租户，请补充租户编码。";
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
  onUnload() {
    this.clearSmsCooldownTimer();
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
      } else if (rawScene === CLIENT_SCENE) {
        this.scene = CLIENT_SCENE;
        this.clientInviteToken = queryToken;
      } else if (rawScene === LAWYER_INVITE_SCENE) {
        this.scene = LAWYER_INVITE_SCENE;
        this.lawyerInviteToken = queryToken;
      } else if (rawScene === WEB_LOGIN_SCENE) {
        this.scene = WEB_LOGIN_SCENE;
        this.webLoginTicket = queryTicket || queryToken;
      } else if (queryToken) {
        this.scene = LAWYER_INVITE_SCENE;
        this.lawyerInviteToken = queryToken;
      }

      this.activeLoginMethod = this.isLawyerInviteMode ? "wechat" : "wechat";
      this.wxSessionTicket = "";
    },
    selectLoginMethod(method) {
      if (this.isLawyerInviteMode && method !== "wechat") {
        return;
      }
      this.activeLoginMethod = method;
      this.clearStatus();
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
    clearSmsCooldownTimer() {
      if (this.smsTimer) {
        clearInterval(this.smsTimer);
        this.smsTimer = null;
      }
    },
    startSmsCooldown(seconds) {
      const nextSeconds = Number(seconds || 0);
      this.clearSmsCooldownTimer();
      this.smsCooldown = nextSeconds > 0 ? nextSeconds : 0;
      if (!this.smsCooldown) {
        return;
      }

      this.smsTimer = setInterval(() => {
        if (this.smsCooldown <= 1) {
          this.smsCooldown = 0;
          this.clearSmsCooldownTimer();
          return;
        }
        this.smsCooldown -= 1;
      }, 1000);
    },
    buildTenantPayload() {
      return {
        tenant_code: this.showTenantCodeInput ? this.tenantCode.trim() || null : null,
        case_invite_token: this.isClientInviteMode ? this.clientInviteToken : null,
      };
    },
    validateTenantCodeIfNeeded() {
      const needTenantCode = this.showTenantCodeInput && Boolean(this.loginAdvice?.requires_tenant_code);
      const tenantCodeMessage = this.showTenantCodeInput ? validateTenantCode(this.tenantCode, needTenantCode) : "";
      if (tenantCodeMessage) {
        showFormError(tenantCodeMessage);
        return false;
      }
      return true;
    },
    async fetchLoginAdviceAndSync(phone) {
      const normalizedPhone = String(phone || "").trim();
      const phoneError = validatePhone(normalizedPhone, "手机号");
      if (phoneError) {
        this.loginAdvice = {
          requires_tenant_code: false,
          requires_admin_approval: false,
          recommended_entry: "web",
        };
        return null;
      }

      const advice = await fetchLoginAdvice({
        phone: normalizedPhone,
        tenant_code: this.showTenantCodeInput ? this.tenantCode.trim() || null : null,
        case_invite_token: this.isClientInviteMode ? this.clientInviteToken : null,
      });
      this.loginAdvice = advice || {
        requires_tenant_code: false,
        requires_admin_approval: false,
        recommended_entry: "web",
      };

      if (advice?.requires_tenant_code && !String(this.tenantCode || "").trim()) {
        this.setStatus("需要租户编码", "当前手机号命中多个租户，请先补充 tenant_code。", "warning");
      } else if (advice?.requires_admin_approval) {
        this.setStatus("等待审批", "账号已创建但待管理员审批。", "warning");
      } else if (advice?.recommended_entry === "mini-program") {
        this.setStatus("建议入口", "当前角色建议优先使用小程序。", "info");
      }
      return advice;
    },
    async requestWechatLoginCode() {
      return new Promise((resolve, reject) => {
        uni.login({
          provider: "weixin",
          success: (result) => {
            const code = result && result.code ? String(result.code) : "";
            if (!code) {
              reject({ message: "未获取到有效微信登录凭证，请重试。" });
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
        this.setStatus("确认成功", "电脑端会话已就绪。", "success");
        setTimeout(() => {
          redirectByRole(user);
        }, 300);
      } catch (error) {
        const message = friendlyError(error, "当前账号无法确认网页登录。");
        this.setStatus("确认失败", message, "warning");
        showFormError(message);
      }
    },
    async finishLogin(payload) {
      const accessToken = payload && payload.access_token ? payload.access_token : "";
      if (!accessToken) {
        throw { message: "登录结果缺少 access_token。" };
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
        throw { message: "未获取到当前用户信息。" };
      }

      const enrichedUser = await this.enrichWorkspaceUser(user);
      setUserInfo(enrichedUser);
      this.wxSessionTicket = "";

      if (this.isWebLoginMode) {
        await this.confirmWebLoginForCurrentUser(enrichedUser);
        return;
      }

      if (enrichedUser.must_reset_password) {
        this.setStatus("需先修改密码", "首次登录请先完成密码修改。", "warning");
        await redirectByRole(enrichedUser);
        return;
      }

      this.setStatus("登录成功", "正在进入工作台。", "success");
      redirectByRole(enrichedUser);
    },
    async handleLoginResult(payload) {
      this.wechatOpenid = payload.wechat_openid || this.wechatOpenid || "";
      if (payload.need_bind_phone) {
        this.wxSessionTicket = payload.wx_session_ticket || "";
        this.setStatus("需要手机号授权", "请继续完成手机号授权。", "info");
        return;
      }
      if (!payload.access_token || payload.login_state === "PENDING_APPROVAL") {
        clearSession();
        this.wxSessionTicket = "";
        this.setStatus("等待审批", "当前账号正在等待管理员审批。", "warning");
        return;
      }
      await this.finishLogin(payload);
    },
    async startWechatLogin() {
      if (!this.validateTenantCodeIfNeeded()) {
        return;
      }
      this.loginSubmitting = true;
      this.wxSessionTicket = "";
      this.clearStatus();
      try {
        const code = await this.requestWechatLoginCode();
        const payload = await wxMiniLogin({
          code,
          case_invite_token: this.isClientInviteMode ? this.clientInviteToken : null,
          lawyer_invite_token: this.isLawyerInviteMode ? this.lawyerInviteToken : null,
        });
        await this.handleLoginResult(payload);
      } catch (error) {
        const message = friendlyError(error, "微信登录失败");
        this.setStatus("登录失败", message, "error");
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
        showFormError("请先完成微信登录。");
        return;
      }
      if (!this.validateTenantCodeIfNeeded()) {
        return;
      }

      const detail = event && event.detail ? event.detail : {};
      const phoneCode = detail && detail.code ? String(detail.code) : "";
      if (!phoneCode) {
        const message = "你已取消手机号授权。";
        this.setStatus("授权已取消", message, "warning");
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
        const message = friendlyError(error, "手机号授权失败");
        this.setStatus("登录失败", message, "error");
        showFormError(message);
      } finally {
        this.phoneSubmitting = false;
      }
    },
    async sendLoginSmsCode() {
      if (!this.validateTenantCodeIfNeeded()) {
        return;
      }

      const phoneError = validatePhone(this.smsForm.phone, "手机号");
      if (phoneErrorAfterAdvice) {
        showFormError(phoneErrorAfterAdvice);
        return;
      }

      this.smsSending = true;
      try {
        const payload = await sendSmsCode({
          phone: this.smsForm.phone.trim(),
          purpose: "login",
        });
        this.startSmsCooldown(payload && payload.retry_after_seconds ? payload.retry_after_seconds : 60);
        this.setStatus("验证码已发送", "请留意短信并在有效期内完成登录。", "info");
      } catch (error) {
        const message = friendlyError(error, "验证码发送失败");
        this.setStatus("发送失败", message, "error");
        showFormError(message);
      } finally {
        this.smsSending = false;
      }
    },
    async submitSmsLogin() {
      if (!this.validateTenantCodeIfNeeded()) {
        return;
      }

      const phoneError = validatePhone(this.smsForm.phone, "手机号");
      if (phoneError) {
        showFormError(phoneError);
        return;
      }
      const codeError = validateSmsCode(this.smsForm.code, "验证码");
      if (codeError) {
        showFormError(codeError);
        return;
      }

      this.smsLoginSubmitting = true;
      this.clearStatus();
      try {
        const payload = await loginBySmsCode({
          phone: this.smsForm.phone.trim(),
          code: this.smsForm.code.trim(),
          ...this.buildTenantPayload(),
        });
        await this.finishLogin(payload);
      } catch (error) {
        const message = friendlyError(error, "验证码登录失败");
        this.setStatus("登录失败", message, "error");
        showFormError(message);
      } finally {
        this.smsLoginSubmitting = false;
      }
    },
    async submitPasswordLogin() {
      try {
        await this.fetchLoginAdviceAndSync(this.passwordForm.phone);
      } catch {
        // Ignore advice preload failures and fall back to existing login flow.
      }

      if (!this.validateTenantCodeIfNeeded()) {
        return;
      }

      const phoneError = validatePhone(this.passwordForm.phone, "手机号");
      if (phoneError) {
        showFormError(phoneError);
        return;
      }
      const passwordError = validatePassword(this.passwordForm.password, "密码");
      if (passwordError) {
        showFormError(passwordError);
        return;
      }

      this.passwordSubmitting = true;
      this.clearStatus();
      try {
        const payload = await loginByPassword({
          phone: this.passwordForm.phone.trim(),
          password: this.passwordForm.password,
          ...this.buildTenantPayload(),
        });
        await this.finishLogin(payload);
      } catch (error) {
        const message = friendlyError(error, "账号密码登录失败");
        this.setStatus("登录失败", message, "error");
        showFormError(message);
      } finally {
        this.passwordSubmitting = false;
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
  line-height: 1.6;
  color: #6e6e73;
}

.field-gap {
  margin-top: 18rpx;
}

.token-text {
  margin-top: 12rpx;
}

.helper-copy {
  display: block;
  margin-top: 14rpx;
}

.method-switch {
  display: flex;
  gap: 12rpx;
  margin-top: 20rpx;
  padding: 10rpx;
  border-radius: 28rpx;
  background: rgba(245, 245, 247, 0.95);
}

.method-chip {
  flex: 1;
  border: 0;
  border-radius: 22rpx;
  background: transparent;
  color: #6e6e73;
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.2;
  padding: 20rpx 12rpx;
}

.method-chip::after {
  border: 0;
}

.method-chip-active {
  background: #1d1d1f;
  color: #ffffff;
}

.inline-action {
  display: flex;
  gap: 16rpx;
  align-items: center;
}

.inline-input {
  flex: 1;
  margin-top: 0;
}

.inline-button {
  width: 220rpx;
  min-width: 220rpx;
}

.primary-button,
.helper-button {
  width: 100%;
}

.helper-button {
  margin-top: 12rpx;
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

