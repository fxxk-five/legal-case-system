<template>
  <view class="page-container">
    <view class="card hero-card">
      <text class="hero-title">微信小程序登录</text>
      <text class="hero-desc">先通过微信身份换取 openid，再决定是绑定已有律师账号还是进入当事人流程。</text>
      <button class="primary-btn" :loading="loggingIn" @click="handleWechatLogin">微信登录</button>
    </view>

    <view v-if="needBind" class="card form-card">
      <text class="section-title">绑定手机号</text>
      <input v-model="form.phone" class="input" placeholder="请输入手机号" />
      <input v-model="form.password" class="input" password placeholder="已有账号请输入密码，新当事人可留空" />
      <input v-model="form.realName" class="input" placeholder="姓名（新建用户时使用）" />
      <picker :range="roleOptions" range-key="label" @change="handleRoleChange">
        <view class="picker">{{ currentRoleLabel }}</view>
      </picker>
      <button class="primary-btn" :loading="binding" @click="handleBind">确认绑定</button>
    </view>
  </view>
</template>

<script setup>
import { onLoad } from "@dcloudio/uni-app";
import { computed, reactive, ref } from "vue";

import { post } from "../../common/http";
import { setAccessToken, setUserInfo, setWechatOpenid } from "../../common/auth";
import { getCurrentUser, redirectByRole } from "../../common/session";

const loggingIn = ref(false);
const binding = ref(false);
const needBind = ref(false);
const roleOptions = [
  { label: "律师", value: "lawyer" },
  { label: "当事人", value: "client" },
];

const form = reactive({
  phone: "",
  password: "",
  realName: "",
  role: "lawyer",
  caseInviteToken: "",
});

const currentRoleLabel = computed(() => {
  const target = roleOptions.find((item) => item.value === form.role);
  return target ? `当前角色：${target.label}` : "请选择角色";
});

function handleRoleChange(event) {
  const index = Number(event.detail.value || 0);
  form.role = roleOptions[index].value;
}

function jumpByRole(user) {
  redirectByRole(user);
}

function handleWechatLogin() {
  loggingIn.value = true;
  uni.login({
    provider: "weixin",
    success: async ({ code }) => {
      try {
        const data = await post("/auth/wx-mini-login", { code });
        setWechatOpenid(data.wechat_openid);
        if (data.need_bind_phone) {
          needBind.value = true;
          return;
        }
        setAccessToken(data.access_token);
        setUserInfo(data.user);
        jumpByRole(data.user);
      } catch (error) {
        uni.showToast({ title: error.detail || "微信登录失败", icon: "none" });
      } finally {
        loggingIn.value = false;
      }
    },
    fail: () => {
      loggingIn.value = false;
      uni.showToast({ title: "未能获取微信登录 code", icon: "none" });
    },
  });
}

async function handleBind() {
  if (!form.phone) {
    uni.showToast({ title: "请输入手机号", icon: "none" });
    return;
  }
  if (form.role === "lawyer" && !form.password) {
    uni.showToast({ title: "绑定律师账号需要输入密码", icon: "none" });
    return;
  }
  binding.value = true;
  try {
    const wechatOpenid = uni.getStorageSync("wechat_openid");
    const data = await post("/auth/wx-mini-bind", {
      wechat_openid: wechatOpenid,
      phone: form.phone,
      password: form.password || null,
      real_name: form.realName || null,
      role: form.role,
      case_invite_token: form.caseInviteToken || null,
    });
    setAccessToken(data.access_token);
    setUserInfo(data.user);
    jumpByRole(data.user);
  } catch (error) {
    uni.showToast({ title: error.detail || "绑定失败", icon: "none" });
  } finally {
    binding.value = false;
  }
}

onLoad((options) => {
  const currentUser = getCurrentUser();
  if (currentUser) {
    redirectByRole(currentUser);
    return;
  }
  form.caseInviteToken = options.token || "";
  if (form.caseInviteToken) {
    form.role = "client";
  }
});
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
