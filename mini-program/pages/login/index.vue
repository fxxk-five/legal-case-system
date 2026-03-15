<template>
  <view class="page-container">
    <view class="card hero-card">
      <text class="hero-title">微信小程序登录</text>
      <text class="hero-desc">先完成微信身份校验，再决定是绑定已有律师账号还是进入当事人流程。</text>
      <button class="primary-btn" :loading="loggingIn" @click="handleWechatLogin">微信登录</button>
    </view>

    <view v-if="needBind" class="card form-card">
      <text class="section-title">绑定手机号</text>
      <input v-model="form.phone" class="input" placeholder="请输入手机号" />
      <text class="form-tip">手机号应为 6 到 20 位数字。</text>
      <input v-model="form.password" class="input" password placeholder="已有账号请输入密码，新当事人可留空" />
      <text class="form-tip">律师绑定已有账号时必须填写密码，密码至少 6 位。</text>
      <input v-model="form.realName" class="input" placeholder="姓名（新建用户时使用）" />
      <text class="form-tip">请输入真实姓名，最多 100 个字符。</text>
      <input
        v-model="form.tenantCode"
        class="input"
        placeholder="租户编码（律师绑定多租户账号时建议填写）"
      />
      <text class="form-tip">租户编码可选；如同一手机号存在多个租户，必须填写。</text>
      <picker :range="roleOptions" range-key="label" @change="handleRoleChange">
        <view class="picker">{{ currentRoleLabel }}</view>
      </picker>
      <button class="primary-btn" :loading="binding" @click="handleBind">确认绑定</button>
    </view>
  </view>
</template>

<script>
import { post } from "../../common/http";
import { setAccessToken, setUserInfo, setWechatOpenid } from "../../common/auth";
import { getCurrentUser, redirectByRole } from "../../common/session";
import {
  friendlyError,
  showFormError,
  validateName,
  validatePassword,
  validatePhone,
  validateTenantCode,
} from "../../common/form";

export default {
  data() {
    return {
      loggingIn: false,
      binding: false,
      needBind: false,
      roleOptions: [
        { label: "律师", value: "lawyer" },
        { label: "当事人", value: "client" },
      ],
      form: {
        phone: "",
        password: "",
        realName: "",
        role: "lawyer",
        tenantCode: "",
        caseInviteToken: "",
      },
    };
  },
  computed: {
    currentRoleLabel() {
      const target = this.roleOptions.find((item) => item.value === this.form.role);
      return target ? `当前身份：${target.label}` : "请选择身份";
    },
  },
  onLoad(options) {
    const currentUser = getCurrentUser();
    if (currentUser) {
      redirectByRole(currentUser);
      return;
    }
    this.form.caseInviteToken = options.token || "";
    if (this.form.caseInviteToken) {
      this.form.role = "client";
    }
  },
  methods: {
    handleRoleChange(event) {
      const index = Number(event.detail.value || 0);
      this.form.role = this.roleOptions[index].value;
    },
    jumpByRole(user) {
      redirectByRole(user);
    },
    handleWechatLogin() {
      this.loggingIn = true;
      uni.login({
        provider: "weixin",
        success: async ({ code }) => {
          try {
            const data = await post("/auth/wx-mini-login", { code });
            setWechatOpenid(data.wechat_openid);
            if (data.need_bind_phone) {
              this.needBind = true;
              return;
            }
            setAccessToken(data.access_token);
            setUserInfo(data.user);
            this.jumpByRole(data.user);
          } catch (error) {
            showFormError(friendlyError(error, "微信登录失败"));
          } finally {
            this.loggingIn = false;
          }
        },
        fail: () => {
          this.loggingIn = false;
          showFormError("未能获取微信登录凭证");
        },
      });
    },
    async handleBind() {
      const validationMessage =
        validatePhone(this.form.phone) ||
        validatePassword(this.form.password, "密码", this.form.role === "lawyer") ||
        validateName(this.form.realName, "姓名") ||
        validateTenantCode(this.form.tenantCode, false);
      if (validationMessage) {
        showFormError(validationMessage);
        return;
      }
      this.binding = true;
      try {
        const wechatOpenid = uni.getStorageSync("wechat_openid");
        const data = await post("/auth/wx-mini-bind", {
          wechat_openid: wechatOpenid,
          phone: this.form.phone,
          password: this.form.password || null,
          real_name: this.form.realName || null,
          tenant_code: this.form.tenantCode || null,
          role: this.form.role,
          case_invite_token: this.form.caseInviteToken || null,
        });
        setAccessToken(data.access_token);
        setUserInfo(data.user);
        this.jumpByRole(data.user);
      } catch (error) {
        showFormError(friendlyError(error, "绑定失败"));
      } finally {
        this.binding = false;
      }
    },
  },
};
</script>

<style scoped>
.hero-card {
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  color: #fff;
}

.hero-title {
  display: block;
  font-size: 42rpx;
  font-weight: 700;
  margin-bottom: 18rpx;
}

.hero-desc {
  display: block;
  line-height: 1.7;
  opacity: 0.88;
  margin-bottom: 28rpx;
}

.form-card {
  margin-top: 24rpx;
}

.form-tip {
  display: block;
  margin: -6rpx 0 18rpx;
  color: rgba(15, 23, 42, 0.62);
  font-size: 24rpx;
  line-height: 1.5;
}

.input,
.picker {
  width: 100%;
  height: 88rpx;
  border-radius: 18rpx;
  background: #f8fafc;
  padding: 0 24rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
}

.primary-btn {
  width: 100%;
  height: 88rpx;
  border: none;
  border-radius: 18rpx;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
}
</style>
