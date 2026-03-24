<template>
  <view class="page-container fade-in">
    <view class="card page-hero">
      <text class="hero-kicker">{{ textMap.kicker }}</text>
      <text class="page-hero-title">{{ textMap.title }}</text>
      <text class="page-hero-desc">{{ textMap.description }}</text>
    </view>

    <view class="card">
      <text class="section-title">{{ textMap.sectionTitle }}</text>
      <text class="meta">{{ textMap.sectionDesc }}</text>
      <view class="toolbar card-toolbar">
        <button class="toolbar-button toolbar-button-primary action-button" @click="redirectToLogin">
          {{ textMap.actionText }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { buildLoginPageUrl } from "../../common/role-routing";

export default {
  data() {
    return {
      targetUrl: buildLoginPageUrl(),
      textMap: {
        kicker: "\u6848\u4ef6",
        title: "\u6848\u4ef6\u9080\u8bf7",
        description: "\u6b63\u5728\u4e3a\u4f60\u8df3\u8f6c\u767b\u5f55\u5e76\u7ed1\u5b9a\u6848\u4ef6\u3002",
        sectionTitle: "\u7ee7\u7eed\u8fdb\u5165",
        sectionDesc: "\u5982\u679c\u6ca1\u6709\u81ea\u52a8\u8df3\u8f6c\uff0c\u53ef\u70b9\u51fb\u4e0b\u65b9\u6309\u94ae\u7ee7\u7eed\u3002",
        actionText: "\u8fdb\u5165\u767b\u5f55\u9875",
      },
    };
  },
  onLoad(options) {
    const token = String(options.token || "").trim();
    const scene = token ? "client-case" : "";
    this.targetUrl = buildLoginPageUrl(token, scene);
    this.redirectToLogin();
  },
  methods: {
    redirectToLogin() {
      uni.redirectTo({ url: this.targetUrl });
    },
  },
};
</script>

<style scoped>
.card-toolbar,
.action-button {
  width: 100%;
}
</style>
