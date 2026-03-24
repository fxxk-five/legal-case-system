<template>
  <view class="page-container fade-in workspace-page">
    <view class="card page-hero">
      <text class="page-hero-title">分析管理</text>
      <text class="page-hero-desc">
        汇总智能分析用量、任务状态、提示词和模型服务设置，律师端与网页端共享同一套分析管理接口与预算约束。
      </text>

    </view>

    <view v-if="loadingPage && !initialized" class="card empty-state">正在加载分析管理数据...</view>

    <template v-else>
      <view class="grid-three metrics-grid">
        <view v-for="item in usageCards" :key="item.key" class="card metric-card">
          <text class="stat-card-title">{{ item.label }}</text>
          <text class="stat-card-value">{{ item.task_count }}</text>
          <text class="stat-card-desc">任务数</text>
          <text class="meta">令牌：{{ item.token_usage_text }}</text>
          <text class="meta">成本：{{ item.cost_total_text }}</text>
        </view>
      </view>

      <view class="card">
        <text class="section-title">任务类型分布</text>
        <view v-if="!taskTypeRows.length" class="empty-state">暂无任务数据。</view>
        <view v-for="item in taskTypeRows" :key="item.key" class="breakdown-row">
          <view class="row-between">
            <text class="breakdown-label">{{ item.label }}</text>
            <text class="meta">{{ item.count }} / {{ item.percent_text }}</text>
          </view>
          <view class="progress-track">
            <view class="progress-fill progress-blue" :style="item.bar_style"></view>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="section-title">任务状态分布</text>
        <view v-if="!statusRows.length" class="empty-state">暂无任务状态数据。</view>
        <view v-for="item in statusRows" :key="item.key" class="breakdown-row">
          <view class="row-between">
            <text class="breakdown-label">{{ item.label }}</text>
            <text class="meta">{{ item.count }} / {{ item.percent_text }}</text>
          </view>
          <view class="progress-track">
            <view class="progress-fill progress-teal" :style="item.bar_style"></view>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="section-title">模型成本分布</text>
        <view v-if="!modelRows.length" class="empty-state">暂无模型调用记录。</view>
        <view v-for="item in modelRows" :key="item.model" class="breakdown-row">
          <view class="row-between row-top">
            <view>
              <text class="breakdown-label">{{ item.model }}</text>
              <text class="meta">结果：{{ item.result_count }} 条 · 令牌：{{ item.token_usage_text }}</text>
            </view>
            <text class="meta">{{ item.cost_total_text }}</text>
          </view>
          <view class="progress-track">
            <view class="progress-fill progress-amber" :style="item.bar_style"></view>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="section-title">任务列表</text>
        <picker class="picker-wrap" :range="taskStatusOptions" range-key="label" :value="taskStatusIndex" @change="onTaskStatusChange">
          <view class="picker-input">{{ taskStatusLabel }}</view>
        </picker>
        <picker class="picker-wrap" :range="taskTypeOptions" range-key="label" :value="taskTypeIndex" @change="onTaskTypeChange">
          <view class="picker-input">{{ taskTypeLabel }}</view>
        </picker>
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" @click="reloadTasks">刷新任务</button>
        </view>
        <text class="meta">当前共 {{ taskTotal }} 条任务记录。</text>

        <view v-if="!taskItems.length" class="empty-state">暂无任务记录。</view>
        <view v-for="item in taskItems" :key="item.task_id" class="task-card">
          <text class="list-card-title">{{ item.task_type_text }}</text>
          <text class="list-card-subtitle">任务编号：{{ item.task_id }}</text>
          <text class="meta">案件编号：{{ item.case_id }}</text>
          <text class="meta">状态：{{ item.status_text }}</text>
          <text class="meta">进度：{{ item.progress }}%</text>
          <text class="meta">创建时间：{{ item.created_at_text }}</text>
          <text class="meta">更新时间：{{ item.updated_at_text }}</text>
          <text class="meta">消息：{{ item.message_text }}</text>
          <view class="progress-track task-progress">
            <view class="progress-fill progress-blue" :style="item.progress_style"></view>
          </view>
          <view class="toolbar card-toolbar">
            <button
              class="toolbar-button toolbar-button-secondary action-button"
              :disabled="!item.can_retry"
              :loading="retryingTaskId === item.task_id"
              @click="retryTaskItem(item)"
            >
              重新入队
            </button>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="section-title">提示词配置</text>
        <text class="meta">当前阶段保留解析、分析、证伪三组提示词入口，后续可继续微调。</text>
        <textarea v-model="promptForm.parse_prompt" class="textarea field-gap" maxlength="20000" placeholder="文档解析提示词" />
        <textarea v-model="promptForm.analyze_prompt" class="textarea field-gap" maxlength="20000" placeholder="法律分析提示词" />
        <textarea v-model="promptForm.falsify_prompt" class="textarea field-gap" maxlength="20000" placeholder="证伪提示词" />
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" :loading="savingPrompts" @click="savePrompts">保存提示词</button>
        </view>
      </view>

      <view class="card">
        <view class="row-between row-top">
          <view>
            <text class="section-title plain-title">模型服务设置</text>
            <text class="meta">支持 OpenAI 兼容模式与官方云模式；若后续云侧锁定配置，租户端将自动只读。</text>
          </view>
          <text class="tag" :class="providerStatusClass">{{ providerStatusText }}</text>
        </view>
        <picker class="picker-wrap" :range="providerOptions" range-key="label" :value="providerIndex" @change="onProviderChange">
          <view class="picker-input">{{ providerLabel }}</view>
        </picker>
        <input v-model="providerForm.base_url" class="input field-gap" :disabled="!provider.editable" maxlength="500" placeholder="服务地址，例如 https://api.example.com/v1" />
        <input v-model="providerForm.model" class="input field-gap" :disabled="!provider.editable" maxlength="100" placeholder="模型名称，例如 gpt-4o-mini" />
        <input v-model="providerForm.api_key" class="input field-gap" :disabled="!provider.editable" maxlength="500" password placeholder="留空则保持当前接口密钥" />
        <text class="meta">当前已保存：{{ provider.api_key_masked || '未设置' }}</text>
        <view class="toolbar card-toolbar">
          <button class="toolbar-button toolbar-button-primary action-button" :disabled="!provider.editable" :loading="savingProvider" @click="saveProvider">保存模型服务</button>
        </view>
      </view>
    </template>

    <workspace-tab-bar current-key="overview" />
  </view>
</template>

<script>
import WorkspaceTabBar from "../../components/WorkspaceTabBar.vue";
import { buildQuery, get, put, retryTask } from "../../common/http";
import { friendlyError, showFormError } from "../../common/form";
import { ensureWorkspaceAccess } from "../../common/workspace";
import { formatDateTime } from "../../common/display";

const TASK_STATUS_OPTIONS = [
  { label: "全部任务状态", value: "" },
  { label: "待处理", value: "pending" },
  { label: "处理中", value: "processing" },
  { label: "已完成", value: "completed" },
  { label: "失败/死信", value: "failed" },
];

const TASK_TYPE_OPTIONS = [
  { label: "全部任务类型", value: "" },
  { label: "文档解析", value: "parse" },
  { label: "法律分析", value: "analyze" },
  { label: "证伪校验", value: "falsify" },
];

const PROVIDER_OPTIONS = [
  { label: "OpenAI 兼容模式", value: "openai_compatible" },
  { label: "官方云模式", value: "official_cloud" },
];

function numberText(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function costText(value) {
  return `¥${Number(value || 0).toFixed(4)}`;
}

function taskTypeText(value) {
  if (value === "parse") {
    return "文档解析";
  }
  if (value === "analyze") {
    return "法律分析";
  }
  if (value === "falsify") {
    return "证伪校验";
  }
  return value || "未设置";
}

function taskStatusText(value) {
  if (value === "queued") {
    return "排队中";
  }
  if (value === "pending") {
    return "待处理";
  }
  if (value === "processing") {
    return "处理中";
  }
  if (value === "completed") {
    return "已完成";
  }
  if (value === "failed") {
    return "失败";
  }
  if (value === "retrying") {
    return "重试中";
  }
  if (value === "dead") {
    return "死信";
  }
  return value || "未设置";
}

function percentText(value, total) {
  if (!total) {
    return "0%";
  }
  return `${Math.min(100, Math.round((Number(value || 0) / Number(total)) * 100))}%`;
}

function progressStyle(percent) {
  return `width:${Math.max(0, Math.min(100, Math.round(Number(percent || 0))))}%;`;
}

function decorateBreakdown(items, total) {
  return (Array.isArray(items) ? items : []).map((item) => ({
    ...item,
    percent_text: percentText(item.count, total),
    bar_style: progressStyle(total ? (Number(item.count || 0) / total) * 100 : 0),
  }));
}

export default {
  components: {
    WorkspaceTabBar,
  },
  data() {
    return {
      initialized: false,
      loadingPage: false,
      savingPrompts: false,
      savingProvider: false,
      retryingTaskId: "",
      usage: {
        day: { task_count: 0, token_usage: 0, cost_total: 0 },
        week: { task_count: 0, token_usage: 0, cost_total: 0 },
        month: { task_count: 0, token_usage: 0, cost_total: 0 },
        task_type_breakdown: [],
        status_breakdown: [],
        model_breakdown: [],
      },
      promptForm: {
        parse_prompt: "",
        analyze_prompt: "",
        falsify_prompt: "",
      },
      provider: {
        provider_type: "openai_compatible",
        base_url: "",
        model: "",
        api_key_masked: "",
        editable: true,
        locked: false,
      },
      providerForm: {
        provider_type: "openai_compatible",
        base_url: "",
        model: "",
        api_key: "",
      },
      providerOptions: PROVIDER_OPTIONS,
      providerIndex: 0,
      taskStatusOptions: TASK_STATUS_OPTIONS,
      taskStatusIndex: 0,
      taskTypeOptions: TASK_TYPE_OPTIONS,
      taskTypeIndex: 0,
      taskTotal: 0,
      taskItems: [],
      taskTypeRows: [],
      statusRows: [],
      modelRows: [],
    };
  },
  computed: {
    usageCards() {
      return [
        { key: "day", label: "近 24 小时", ...this.decorateWindow(this.usage.day) },
        { key: "week", label: "近 7 天", ...this.decorateWindow(this.usage.week) },
        { key: "month", label: "近 30 天", ...this.decorateWindow(this.usage.month) },
      ];
    },
    taskStatusLabel() {
      const current = this.taskStatusOptions[this.taskStatusIndex];
      return current ? current.label : "全部任务状态";
    },
    taskTypeLabel() {
      const current = this.taskTypeOptions[this.taskTypeIndex];
      return current ? current.label : "全部任务类型";
    },
    providerLabel() {
      const current = this.providerOptions[this.providerIndex];
      return current ? current.label : "OpenAI 兼容模式";
    },
    providerStatusText() {
      return this.provider.locked ? "已锁定" : "可编辑";
    },
    providerStatusClass() {
      return this.provider.locked ? "tag-warning" : "tag-success";
    },
  },
  onShow() {
    const user = ensureWorkspaceAccess({ adminOnly: true });
    if (!user) {
      return;
    }
    this.loadAll();
  },
  methods: {
    decorateWindow(item) {
      return {
        task_count: Number(item.task_count || 0),
        token_usage_text: numberText(item.token_usage),
        cost_total_text: costText(item.cost_total),
      };
    },
    decorateTaskItem(item) {
      return {
        ...item,
        task_type_text: taskTypeText(item.task_type),
        status_text: taskStatusText(item.status),
        created_at_text: formatDateTime(item.created_at, "-"),
        updated_at_text: formatDateTime(item.updated_at, "-"),
        progress_style: progressStyle(item.progress),
        message_text: item.message || item.error_message || "-",
        can_retry: ["failed", "dead"].includes(String(item.status || "").toLowerCase()),
      };
    },
    rebuildBreakdowns() {
      const taskTotal = (this.usage.task_type_breakdown || []).reduce((sum, item) => sum + Number(item.count || 0), 0);
      const statusTotal = (this.usage.status_breakdown || []).reduce((sum, item) => sum + Number(item.count || 0), 0);
      const modelTotal = (this.usage.model_breakdown || []).reduce((sum, item) => sum + Number(item.cost_total || 0), 0);

      this.taskTypeRows = decorateBreakdown(this.usage.task_type_breakdown, taskTotal);
      this.statusRows = decorateBreakdown(this.usage.status_breakdown, statusTotal);
      this.modelRows = (Array.isArray(this.usage.model_breakdown) ? this.usage.model_breakdown : []).map((item) => ({
        ...item,
        token_usage_text: numberText(item.token_usage),
        cost_total_text: costText(item.cost_total),
        bar_style: progressStyle(modelTotal ? (Number(item.cost_total || 0) / modelTotal) * 100 : 0),
      }));
    },
    async loadUsage() {
      const data = await get("/analytics/ai-usage");
      this.usage = {
        day: data.day || { task_count: 0, token_usage: 0, cost_total: 0 },
        week: data.week || { task_count: 0, token_usage: 0, cost_total: 0 },
        month: data.month || { task_count: 0, token_usage: 0, cost_total: 0 },
        task_type_breakdown: Array.isArray(data.task_type_breakdown) ? data.task_type_breakdown : [],
        status_breakdown: Array.isArray(data.status_breakdown) ? data.status_breakdown : [],
        model_breakdown: Array.isArray(data.model_breakdown) ? data.model_breakdown : [],
      };
      this.rebuildBreakdowns();
    },
    async loadPrompts() {
      const data = await get("/analytics/prompts");
      this.promptForm.parse_prompt = data.parse_prompt || "";
      this.promptForm.analyze_prompt = data.analyze_prompt || "";
      this.promptForm.falsify_prompt = data.falsify_prompt || "";
    },
    async loadProvider() {
      const data = await get("/analytics/provider-settings");
      this.provider = {
        provider_type: data.provider_type || "openai_compatible",
        base_url: data.base_url || "",
        model: data.model || "",
        api_key_masked: data.api_key_masked || "",
        editable: Boolean(data.editable),
        locked: Boolean(data.locked),
      };
      this.providerForm.provider_type = this.provider.provider_type;
      this.providerForm.base_url = this.provider.base_url;
      this.providerForm.model = this.provider.model;
      this.providerForm.api_key = "";
      const providerIndex = this.providerOptions.findIndex((item) => item.value === this.provider.provider_type);
      this.providerIndex = providerIndex >= 0 ? providerIndex : 0;
    },
    async loadTasks() {
      const params = {
        page: 1,
        page_size: 20,
        status: this.taskStatusOptions[this.taskStatusIndex] ? this.taskStatusOptions[this.taskStatusIndex].value : "",
        task_type: this.taskTypeOptions[this.taskTypeIndex] ? this.taskTypeOptions[this.taskTypeIndex].value : "",
      };
      const data = await get(`/ai/tasks${buildQuery(params)}`);
      this.taskTotal = Number(data.total || 0);
      this.taskItems = Array.isArray(data.items) ? data.items.map((item) => this.decorateTaskItem(item)) : [];
    },
    async loadAll() {
      this.loadingPage = true;
      try {
        await Promise.all([this.loadUsage(), this.loadPrompts(), this.loadProvider(), this.loadTasks()]);
        this.initialized = true;
      } catch (error) {
        showFormError(friendlyError(error, "加载分析管理数据失败"));
      } finally {
        this.loadingPage = false;
      }
    },
    onTaskStatusChange(event) {
      this.taskStatusIndex = Number(event.detail.value || 0);
      this.reloadTasks();
    },
    onTaskTypeChange(event) {
      this.taskTypeIndex = Number(event.detail.value || 0);
      this.reloadTasks();
    },
    onProviderChange(event) {
      const index = Number(event.detail.value || 0);
      this.providerIndex = Number.isNaN(index) ? 0 : index;
      const current = this.providerOptions[this.providerIndex] || this.providerOptions[0];
      this.providerForm.provider_type = current.value;
    },
    async retryTaskItem(item) {
      if (!item.can_retry) {
        return;
      }
      this.retryingTaskId = item.task_id;
      try {
        await retryTask(item.task_id, "manual retry from mini-program analytics console");
        uni.showToast({ title: "已重新入队", icon: "success" });
        await this.loadTasks();
        await this.loadUsage();
      } catch (error) {
        showFormError(friendlyError(error, "任务重试失败"));
      } finally {
        this.retryingTaskId = "";
      }
    },
    async reloadTasks() {
      try {
        await this.loadTasks();
      } catch (error) {
        showFormError(friendlyError(error, "加载任务列表失败"));
      }
    },
    async savePrompts() {
      this.savingPrompts = true;
      try {
        await put("/analytics/prompts", { ...this.promptForm });
        uni.showToast({ title: "提示词已保存", icon: "success" });
        await this.loadPrompts();
      } catch (error) {
        showFormError(friendlyError(error, "保存提示词失败"));
      } finally {
        this.savingPrompts = false;
      }
    },
    async saveProvider() {
      if (!this.provider.editable) {
        showFormError("当前模型服务配置已锁定");
        return;
      }
      this.savingProvider = true;
      try {
        await put("/analytics/provider-settings", { ...this.providerForm });
        uni.showToast({ title: "模型服务已保存", icon: "success" });
        await this.loadProvider();
      } catch (error) {
        showFormError(friendlyError(error, "保存模型服务失败"));
      } finally {
        this.savingProvider = false;
      }
    },
  },
};
</script>

<style scoped>
.metrics-grid {
  margin-bottom: 0;
}

.metric-card {
  margin-bottom: 24rpx;
}

.picker-wrap,
.field-gap {
  margin-bottom: 18rpx;
}

.card-toolbar {
  margin-top: 18rpx;
}

.action-button {
  width: 100%;
}

.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.row-top {
  align-items: flex-start;
}

.plain-title::before {
  display: none;
}

.breakdown-row,
.task-card {
  padding: 24rpx 0;
  border-top: 1rpx solid #e2e8f0;
}

.breakdown-row:first-of-type,
.task-card:first-of-type {
  border-top: 0;
  padding-top: 8rpx;
}

.breakdown-label {
  display: block;
  color: #0f172a;
  font-weight: 600;
}

.progress-track {
  margin-top: 12rpx;
  height: 10rpx;
  border-radius: 999rpx;
  background: #e2e8f0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
}

.progress-blue {
  background: linear-gradient(90deg, #1d4ed8, #38bdf8);
}

.progress-teal {
  background: linear-gradient(90deg, #0f766e, #22c55e);
}

.progress-amber {
  background: linear-gradient(90deg, #d97706, #f59e0b);
}

.task-progress {
  margin-top: 16rpx;
}

.textarea {
  width: 100%;
  min-height: 220rpx;
  padding: 20rpx 24rpx;
  border-radius: 18rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  box-sizing: border-box;
  color: #0f172a;
  line-height: 1.7;
}
</style>
