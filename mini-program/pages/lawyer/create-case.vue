<template>
  <view class="page-container">
    <view class="card">
      <text class="section-title">新建案件</text>
      <input v-model="form.caseNumber" class="input" placeholder="案号" />
      <input v-model="form.title" class="input" placeholder="案件标题" />
      <input v-model="form.clientPhone" class="input" placeholder="当事人手机号" />
      <input v-model="form.clientRealName" class="input" placeholder="当事人姓名" />
      <button class="primary-btn" :loading="submitting" @click="submit">创建案件</button>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from "vue";

import { post } from "../../common/http";

const submitting = ref(false);
const form = reactive({
  caseNumber: "",
  title: "",
  clientPhone: "",
  clientRealName: "",
});

async function submit() {
  if (!form.caseNumber || !form.title || !form.clientPhone || !form.clientRealName) {
    uni.showToast({ title: "请完整填写案件信息", icon: "none" });
    return;
  }
  submitting.value = true;
  try {
    const result = await post("/cases", {
      case_number: form.caseNumber,
      title: form.title,
      client_phone: form.clientPhone,
      client_real_name: form.clientRealName,
    });
    uni.showToast({ title: "创建成功", icon: "success" });
    setTimeout(() => {
      uni.redirectTo({ url: `/pages/lawyer/case-detail?id=${result.id}` });
    }, 500);
  } catch (error) {
    uni.showToast({ title: error.detail || "创建失败", icon: "none" });
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
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
  background: #2563eb;
  color: #fff;
}
</style>
