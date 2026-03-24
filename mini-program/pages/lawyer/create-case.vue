<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">新建案件</text>
      <text class="page-hero-desc">
        案号支持手动输入；如果留空，系统会按租户、年份、法律类型和序号自动生成。
      </text>
    </view>

    <view class="card">
      <text class="section-title">案件基础信息</text>

      <input v-model="form.caseNumber" class="input field-gap" maxlength="100" placeholder="案号（可选）" />
      <text class="meta helper-gap">不填写时系统将自动生成案号。</text>

      <input v-model="form.title" class="input field-gap" maxlength="255" placeholder="案件名称" />

      <picker class="picker-wrap" :range="legalTypeOptions" range-key="label" :value="legalTypeIndex" @change="onLegalTypeChange">
        <view class="picker-input">{{ legalTypeLabel }}</view>
      </picker>

      <picker class="picker-wrap" mode="date" :value="form.deadlineDate" @change="onDeadlineDateChange">
        <view class="picker-input">{{ form.deadlineDate || "截止日期（可选）" }}</view>
      </picker>

      <picker class="picker-wrap" mode="time" :value="form.deadlineTime" @change="onDeadlineTimeChange">
        <view class="picker-input">{{ form.deadlineTime || "截止时间（可选）" }}</view>
      </picker>
    </view>

    <view class="card">
      <text class="section-title">当事人信息</text>

      <input v-model="form.clientRealName" class="input field-gap" maxlength="100" placeholder="当事人姓名" />
      <input v-model="form.clientPhone" class="input field-gap" maxlength="11" placeholder="当事人手机号" />

      <view class="toolbar">
        <button class="toolbar-button toolbar-button-secondary action-button" @click="backToCases">返回案件管理</button>
        <button class="toolbar-button toolbar-button-primary action-button" :loading="submitting" @click="submit">创建案件</button>
      </view>
    </view>

    <workspace-tab-bar current-key="cases" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { buildWorkspaceCaseDetailUrl, getWorkspaceModuleUrl } from "../../common/role-routing";
import { LEGAL_TYPE_OPTIONS } from "../../common/display";
import { post } from "../../common/http";
import { friendlyError, showFormError, validateName, validatePhone, validateTitle } from "../../common/form";
import { ensureWorkspaceAccess } from "../../common/workspace";

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      submitting: false,
      legalTypeOptions: LEGAL_TYPE_OPTIONS.filter((item) => item.value),
      legalTypeIndex: 0,
      form: {
        caseNumber: "",
        title: "",
        legalType: "civil_loan",
        deadlineDate: "",
        deadlineTime: "",
        clientPhone: "",
        clientRealName: "",
      },
    };
  },
  computed: {
    legalTypeLabel() {
      const current = this.legalTypeOptions[this.legalTypeIndex];
      return current ? current.label : "请选择法律类型";
    },
  },
  onLoad() {
    const user = ensureWorkspaceAccess();
    if (!user) {
      return;
    }
  },
  methods: {
    onLegalTypeChange(event) {
      const nextIndex = Number(event.detail.value || 0);
      this.legalTypeIndex = Number.isNaN(nextIndex) ? 0 : nextIndex;
      this.form.legalType = this.legalTypeOptions[this.legalTypeIndex].value;
    },
    onDeadlineDateChange(event) {
      this.form.deadlineDate = event.detail.value || "";
    },
    onDeadlineTimeChange(event) {
      this.form.deadlineTime = event.detail.value || "";
    },
    backToCases() {
      uni.redirectTo({ url: getWorkspaceModuleUrl("cases") });
    },
    async submit() {
      const caseNumberValidation = this.form.caseNumber
        ? validateTitle(this.form.caseNumber, "案号", 100)
        : "";
      const validationMessage =
        caseNumberValidation ||
        validateTitle(this.form.title, "案件名称", 255) ||
        validateName(this.form.clientRealName, "当事人姓名") ||
        validatePhone(this.form.clientPhone, "当事人手机号");

      if (validationMessage) {
        showFormError(validationMessage);
        return;
      }

      this.submitting = true;
      try {
        const deadline =
          this.form.deadlineDate && this.form.deadlineTime
            ? `${this.form.deadlineDate}T${this.form.deadlineTime}:00`
            : null;
        const result = await post("/cases", {
          case_number: this.form.caseNumber.trim() || null,
          title: this.form.title.trim(),
          legal_type: this.form.legalType,
          deadline,
          client_phone: this.form.clientPhone.trim(),
          client_real_name: this.form.clientRealName.trim(),
        });

        uni.showToast({ title: "创建成功", icon: "success" });
        setTimeout(() => {
          uni.redirectTo({ url: buildWorkspaceCaseDetailUrl(result.id) });
        }, 400);
      } catch (error) {
        showFormError(friendlyError(error, "创建案件失败"));
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.field-gap,
.picker-wrap {
  margin-bottom: 18rpx;
}

.helper-gap {
  margin-top: -6rpx;
  margin-bottom: 18rpx;
}

.action-button {
  width: 100%;
}
</style>
