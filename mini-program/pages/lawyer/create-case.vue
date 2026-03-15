<template>
  <view class="page-container">
    <view class="card">
      <text class="section-title">新建案件</text>
      <input v-model="form.caseNumber" class="input" placeholder="案号" />
      <text class="form-tip">案号最多 100 个字符，建议使用清晰统一的编号规则。</text>
      <input v-model="form.title" class="input" placeholder="案件标题" />
      <text class="form-tip">案件标题最多 255 个字符。</text>
      <input v-model="form.clientPhone" class="input" placeholder="当事人手机号" />
      <text class="form-tip">请输入 6 到 20 位数字。</text>
      <input v-model="form.clientRealName" class="input" placeholder="当事人姓名" />
      <text class="form-tip">请输入真实姓名，最多 100 个字符。</text>
      <button class="primary-btn" :loading="submitting" @click="submit">创建案件</button>
    </view>
  </view>
</template>

<script>
import { post } from "../../common/http";
import { friendlyError, showFormError, validateName, validatePhone, validateTitle } from "../../common/form";

export default {
  data() {
    return {
      submitting: false,
      form: {
        caseNumber: "",
        title: "",
        clientPhone: "",
        clientRealName: "",
      },
    };
  },
  methods: {
    async submit() {
      const validationMessage =
        validateTitle(this.form.caseNumber, "案号", 100) ||
        validateTitle(this.form.title, "案件标题", 255) ||
        validatePhone(this.form.clientPhone, "当事人手机号") ||
        validateName(this.form.clientRealName, "当事人姓名");
      if (validationMessage) {
        showFormError(validationMessage);
        return;
      }

      this.submitting = true;
      try {
        const result = await post("/cases", {
          case_number: this.form.caseNumber,
          title: this.form.title,
          client_phone: this.form.clientPhone,
          client_real_name: this.form.clientRealName,
        });
        uni.showToast({ title: "创建成功", icon: "success" });
        setTimeout(() => {
          uni.redirectTo({ url: `/pages/lawyer/case-detail?id=${result.id}` });
        }, 500);
      } catch (error) {
        showFormError(friendlyError(error, "创建失败"));
      } finally {
        this.submitting = false;
      }
    },
  },
};
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

.form-tip {
  display: block;
  margin: -6rpx 0 18rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.5;
}

.primary-btn {
  width: 100%;
  height: 88rpx;
  border-radius: 18rpx;
  background: #2563eb;
  color: #fff;
}
</style>
