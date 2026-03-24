<template>
  <view class="remark-panel">
    <view class="remark-header">
      <text class="section-title remark-title">{{ title }}</text>
      <text v-if="hint" class="remark-hint">{{ hint }}</text>
    </view>

    <view v-if="showExistingRemark && normalizedExistingRemark" class="remark-existing">
      <text class="remark-existing-label">{{ existingLabel }}</text>
      <text class="remark-existing-content">{{ normalizedExistingRemark }}</text>
    </view>

    <view class="remark-editor" :class="{ 'remark-editor-disabled': isBusy }">
      <textarea
        class="remark-textarea"
        :value="inputText"
        :maxlength="maxLength"
        :placeholder="placeholder"
        :disabled="isBusy"
        auto-height
        cursor-spacing="24"
        @input="handleInput"
      />

      <view class="remark-toolbar">
        <text class="remark-count" :class="{ 'remark-count-warning': isNearLimit }">
          {{ currentLength }} / {{ maxLength }}
        </text>

        <view class="remark-actions">
          <view
            v-if="showVoice"
            class="voice-button"
            :class="{
              'voice-button-recording': isRecording,
              'voice-button-disabled': isBusy,
            }"
            @touchstart.prevent="startRecording"
            @touchend.prevent="stopRecording"
            @touchcancel.prevent="cancelRecording"
          >
            <text class="voice-button-icon">{{ isRecording ? "●" : "🎤" }}</text>
            <text class="voice-button-text">{{ isRecording ? "松开结束" : "按住说话" }}</text>
          </view>

          <button
            class="toolbar-button toolbar-button-primary remark-submit"
            :disabled="!canSubmit"
            :loading="isSubmitting"
            @click="handleSubmit"
          >
            {{ submitLabel }}
          </button>
        </view>
      </view>
    </view>

    <text v-if="isRecording" class="remark-status">正在录音，松开后自动转成文字。</text>
    <text v-else-if="isTranscribing" class="remark-status">正在识别语音，请稍候...</text>
  </view>
</template>

<script>
import { friendlyError, showFormError } from "../common/form";
import { transcribeCaseRemarkAudio } from "../common/cases";

export default {
  name: "CaseRemarkInput",
  props: {
    title: {
      type: String,
      default: "补充说明",
    },
    hint: {
      type: String,
      default: "",
    },
    placeholder: {
      type: String,
      default: "请输入补充说明...",
    },
    submitLabel: {
      type: String,
      default: "保存",
    },
    maxLength: {
      type: Number,
      default: 2000,
    },
    showVoice: {
      type: Boolean,
      default: false,
    },
    existingLabel: {
      type: String,
      default: "已保存内容",
    },
    existingRemark: {
      type: String,
      default: "",
    },
    showExistingRemark: {
      type: Boolean,
      default: true,
    },
    prefillText: {
      type: String,
      default: "",
    },
    clearOnSubmit: {
      type: Boolean,
      default: true,
    },
    allowEmptySubmit: {
      type: Boolean,
      default: false,
    },
    successText: {
      type: String,
      default: "保存成功",
    },
    submitHandler: {
      type: Function,
      default: null,
    },
  },
  data() {
    return {
      inputText: String(this.prefillText || ""),
      isRecording: false,
      isTranscribing: false,
      isSubmitting: false,
      recorderManager: null,
      recordingCancelled: false,
    };
  },
  computed: {
    currentLength() {
      return this.inputText.length;
    },
    trimmedInput() {
      return String(this.inputText || "").trim();
    },
    normalizedExistingRemark() {
      return String(this.existingRemark || "").trim();
    },
    canSubmit() {
      if (this.isBusy) {
        return false;
      }
      if (this.allowEmptySubmit) {
        return Boolean(this.trimmedInput.length || String(this.prefillText || "").trim().length);
      }
      return this.trimmedInput.length > 0;
    },
    isNearLimit() {
      return this.currentLength >= Math.floor(this.maxLength * 0.9);
    },
    isBusy() {
      return this.isSubmitting || this.isRecording || this.isTranscribing;
    },
  },
  watch: {
    prefillText(nextValue) {
      const nextText = String(nextValue || "");
      if (nextText !== this.inputText && !this.isRecording && !this.isTranscribing) {
        this.inputText = nextText;
      }
    },
  },
  beforeUnmount() {
    this.cleanupRecorder();
  },
  beforeDestroy() {
    this.cleanupRecorder();
  },
  methods: {
    cleanupRecorder() {
      if (!this.isRecording || !this.recorderManager) {
        return;
      }
      this.recordingCancelled = true;
      try {
        this.recorderManager.stop();
      } catch (error) {
        console.warn("stop recorder failed", error);
      }
    },
    handleInput(event) {
      this.inputText = String(event?.detail?.value || "").slice(0, this.maxLength);
      this.$emit("input-change", this.inputText);
    },
    async handleSubmit() {
      if (!this.canSubmit) {
        return;
      }

      const text = this.trimmedInput;

      this.isSubmitting = true;
      try {
        let result = null;
        if (typeof this.submitHandler === "function") {
          result = await this.submitHandler(text);
        } else {
          this.$emit("submit", text);
        }

        if (this.clearOnSubmit) {
          this.inputText = "";
        } else {
          this.inputText = text;
        }

        uni.showToast({
          title: this.successText,
          icon: "success",
        });
        this.$emit("submitted", { text, result });
      } catch (error) {
        showFormError(friendlyError(error, "保存失败，请稍后重试"));
      } finally {
        this.isSubmitting = false;
      }
    },
    ensureRecorderManager() {
      if (this.recorderManager) {
        return this.recorderManager;
      }

      if (!uni.getRecorderManager) {
        throw { message: "当前环境不支持录音，请改用文字输入" };
      }

      this.recorderManager = uni.getRecorderManager();
      this.recorderManager.onStop(this.handleRecorderStop);
      this.recorderManager.onError((error) => {
        this.isRecording = false;
        showFormError(friendlyError(error, "录音失败，请重试"));
      });
      return this.recorderManager;
    },
    ensureRecordPermission() {
      return new Promise((resolve, reject) => {
        uni.getSetting({
          success: ({ authSetting = {} }) => {
            if (authSetting["scope.record"]) {
              resolve(true);
              return;
            }

            uni.authorize({
              scope: "scope.record",
              success: () => resolve(true),
              fail: () => {
                uni.showModal({
                  title: "需要麦克风权限",
                  content: "开启麦克风权限后，才可以使用语音补充说明。",
                  confirmText: "去设置",
                  success: (res) => {
                    if (res.confirm) {
                      uni.openSetting();
                    }
                    reject({ message: "麦克风权限未开启" });
                  },
                  fail: () => reject({ message: "麦克风权限未开启" }),
                });
              },
            });
          },
          fail: () => reject({ message: "无法获取录音权限状态" }),
        });
      });
    },
    async startRecording() {
      if (!this.showVoice || this.isBusy) {
        return;
      }

      try {
        await this.ensureRecordPermission();
        this.recordingCancelled = false;
        this.isRecording = true;
        this.ensureRecorderManager().start({
          duration: 60000,
          sampleRate: 16000,
          numberOfChannels: 1,
          encodeBitRate: 48000,
          format: "mp3",
        });
      } catch (error) {
        if (error?.message) {
          showFormError(friendlyError(error, "无法开始录音"));
        }
      }
    },
    stopRecording() {
      if (!this.isRecording || !this.recorderManager) {
        return;
      }
      this.isRecording = false;
      this.recorderManager.stop();
    },
    cancelRecording() {
      if (!this.isRecording || !this.recorderManager) {
        return;
      }
      this.recordingCancelled = true;
      this.isRecording = false;
      this.recorderManager.stop();
      uni.showToast({
        title: "已取消录音",
        icon: "none",
      });
    },
    async handleRecorderStop(recordResult) {
      if (this.recordingCancelled) {
        this.recordingCancelled = false;
        return;
      }

      const filePath = recordResult?.tempFilePath || "";
      if (!filePath) {
        showFormError("录音文件生成失败，请重试");
        return;
      }

      this.isTranscribing = true;
      uni.showLoading({ title: "识别中..." });
      try {
        const recognizedText = await transcribeCaseRemarkAudio(filePath);
        this.mergeRecognizedText(recognizedText);
        uni.showToast({
          title: "语音已转文字",
          icon: "success",
        });
      } catch (error) {
        showFormError(friendlyError(error, "语音识别失败，请改用文字输入"));
      } finally {
        uni.hideLoading();
        this.isTranscribing = false;
      }
    },
    mergeRecognizedText(text) {
      const nextText = String(text || "").trim();
      if (!nextText) {
        return;
      }
      const separator = this.inputText.trim() ? "，" : "";
      this.inputText = `${this.inputText}${separator}${nextText}`.slice(0, this.maxLength);
      this.$emit("input-change", this.inputText);
    },
  },
};
</script>

<style scoped>
.remark-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.remark-title {
  margin-bottom: 0;
}

.remark-hint {
  flex-shrink: 0;
  color: var(--text-tertiary);
  font-size: 22rpx;
}

.remark-existing {
  margin-bottom: 18rpx;
  padding: 20rpx 22rpx;
  border-radius: 24rpx;
  background: rgba(0, 113, 227, 0.08);
  border: 1rpx solid rgba(0, 113, 227, 0.12);
}

.remark-existing-label,
.remark-existing-content,
.remark-status {
  display: block;
}

.remark-existing-label {
  color: var(--accent-color);
  font-size: 22rpx;
  font-weight: 600;
}

.remark-existing-content {
  margin-top: 10rpx;
  color: var(--text-main);
  font-size: 26rpx;
  line-height: 1.7;
  white-space: pre-wrap;
}

.remark-editor {
  padding: 20rpx 22rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.84);
  border: 1rpx solid rgba(29, 29, 31, 0.06);
}

.remark-editor-disabled {
  opacity: 0.9;
}

.remark-textarea {
  width: 100%;
  min-height: 180rpx;
  color: var(--text-main);
  font-size: 28rpx;
  line-height: 1.7;
}

.remark-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  margin-top: 16rpx;
}

.remark-count {
  flex-shrink: 0;
  color: var(--text-tertiary);
  font-size: 22rpx;
}

.remark-count-warning {
  color: var(--warning-color);
}

.remark-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12rpx;
  flex: 1;
}

.voice-button {
  min-width: 176rpx;
  min-height: 76rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(0, 113, 227, 0.12);
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent-color);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  box-sizing: border-box;
}

.voice-button-recording {
  border-color: rgba(201, 52, 44, 0.14);
  background: rgba(201, 52, 44, 0.1);
  color: var(--danger-color);
}

.voice-button-disabled,
.remark-submit[disabled] {
  opacity: 0.55;
}

.voice-button-icon {
  font-size: 26rpx;
  line-height: 1;
}

.voice-button-text {
  font-size: 22rpx;
  font-weight: 600;
}

.remark-submit {
  min-width: 220rpx;
}

.remark-status {
  margin-top: 12rpx;
  color: var(--warning-color);
  font-size: 22rpx;
  line-height: 1.6;
}
</style>
