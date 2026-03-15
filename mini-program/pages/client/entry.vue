<template>
  <view class="page-container">
    <view class="card">
      <text class="section-title">当事人进入案件</text>
      <text class="desc">扫码进入后，先完成微信登录，再绑定手机号，即可查看案件进度和上传材料。</text>
      <input v-model="phone" class="input" placeholder="手机号" />
      <text class="form-tip">请输入 6 到 20 位数字。</text>
      <input v-model="realName" class="input" placeholder="姓名" />
      <text class="form-tip">请输入真实姓名，最多 100 个字符。</text>
      <button class="primary-btn" :loading="submitting" @click="submit">微信登录并绑定</button>
    </view>
  </view>
</template>

<script>
import { post } from "../../common/http";
import { setAccessToken, setUserInfo, setWechatOpenid } from "../../common/auth";
import { getCurrentUser, redirectByRole } from "../../common/session";
import { friendlyError, showFormError, validateName, validatePhone } from "../../common/form";

export default {
  data() {
    return {
      token: "",
      phone: "",
      realName: "",
      submitting: false,
    };
  },
  onLoad(options) {
    const currentUser = getCurrentUser();
    if (currentUser) {
      redirectByRole(currentUser);
      return;
    }
    this.token = options.token || "";
  },
  methods: {
    submit() {
      const validationMessage =
        validatePhone(this.phone) ||
        validateName(this.realName, "姓名");
      if (validationMessage) {
        showFormError(validationMessage);
        return;
      }
      this.submitting = true;
      uni.login({
        provider: "weixin",
        success: async ({ code }) => {
          try {
            const loginResult = await post("/auth/wx-mini-login", { code });
            setWechatOpenid(loginResult.wechat_openid);
            const bindResult = await post("/auth/wx-mini-bind", {
              wechat_openid: loginResult.wechat_openid,
              phone: this.phone,
              real_name: this.realName,
              role: "client",
              case_invite_token: this.token,
            });
            setAccessToken(bindResult.access_token);
            setUserInfo(bindResult.user);
            redirectByRole(bindResult.user);
          } catch (error) {
            showFormError(friendlyError(error, "进入案件失败"));
          } finally {
            this.submitting = false;
          }
        },
        fail: () => {
          this.submitting = false;
          showFormError("微信登录失败");
        },
      });
    },
  },
};
</script>

<style scoped>
.desc {
  display: block;
  line-height: 1.7;
  color: #475569;
  margin-bottom: 24rpx;
}

.form-tip {
  display: block;
  margin: -6rpx 0 18rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.5;
}

.input {
  width: 100%;
  height: 88rpx;
  border-radius: 18rpx;
  background: #f8fafc;
  padding: 0 24rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
}

.primary-btn {
  width: 100%;
  height: 88rpx;
  border-radius: 18rpx;
  background: #0f766e;
  color: #fff;
}
</style>
