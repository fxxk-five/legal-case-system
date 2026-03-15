<template>
  <view class="page-container">
    <view class="card">
      <text class="section-title">当事人进入案件</text>
      <text class="desc">扫码进入后，先完成微信登录，再绑定手机号，即可查看案件进度和上传材料。</text>
      <input v-model="phone" class="input" placeholder="手机号" />
      <input v-model="realName" class="input" placeholder="姓名" />
      <button class="primary-btn" :loading="submitting" @click="submit">微信登录并绑定</button>
    </view>
  </view>
</template>

<script setup>
import { onLoad } from "@dcloudio/uni-app";
import { ref } from "vue";

import { post } from "../../common/http";
import { setAccessToken, setUserInfo, setWechatOpenid } from "../../common/auth";
import { getCurrentUser, redirectByRole } from "../../common/session";

const token = ref("");
const phone = ref("");
const realName = ref("");
const submitting = ref(false);

onLoad((options) => {
  const currentUser = getCurrentUser();
  if (currentUser) {
    redirectByRole(currentUser);
    return;
  }
  token.value = options.token || "";
});

function submit() {
  if (!phone.value || !realName.value) {
    uni.showToast({ title: "请输入手机号和姓名", icon: "none" });
    return;
  }
  submitting.value = true;
  uni.login({
    provider: "weixin",
    success: async ({ code }) => {
      try {
        const loginResult = await post("/auth/wx-mini-login", { code });
        setWechatOpenid(loginResult.wechat_openid);
        const bindResult = await post("/auth/wx-mini-bind", {
          wechat_openid: loginResult.wechat_openid,
          phone: phone.value,
          real_name: realName.value,
          role: "client",
          case_invite_token: token.value,
        });
        setAccessToken(bindResult.access_token);
        setUserInfo(bindResult.user);
        redirectByRole(bindResult.user);
      } catch (error) {
        uni.showToast({ title: error.detail || "进入案件失败", icon: "none" });
      } finally {
        submitting.value = false;
      }
    },
    fail: () => {
      submitting.value = false;
      uni.showToast({ title: "微信登录失败", icon: "none" });
    },
  });
}
</script>

<style scoped>
.desc {
  display: block;
  line-height: 1.7;
  color: #475569;
  margin-bottom: 24rpx;
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
