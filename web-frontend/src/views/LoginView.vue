<template>
  <section class="login-page">
    <div class="login-panel">
      <div class="login-copy">
        <p class="eyebrow">法律案件系统</p>
        <h1>律所案件管理后台</h1>
        <p>当前已切换到多租户主流程。你可以登录现有租户，也可以直接创建个人空间、创建律所，或者申请加入机构。</p>
      </div>

      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form class="login-form" :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item label="租户编码">
              <el-input v-model="loginForm.tenant_code" placeholder="多租户场景建议填写，例如 org-demo" />
              <div class="field-tip">可留空；如果同一个手机号存在于多个租户，必须填写租户编码。</div>
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="loginForm.phone" placeholder="请输入手机号" />
              <div class="field-tip">请输入 6 到 20 位数字。</div>
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" />
              <div class="field-tip">密码至少 6 位。</div>
            </el-form-item>
            <el-button class="login-button" type="primary" :loading="submitting" @click="handleLogin">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="创建个人空间" name="personal">
          <el-form class="login-form" :model="personalForm">
            <el-form-item label="工作空间名称">
              <el-input v-model="personalForm.workspace_name" placeholder="例如 张三律师工作台" />
              <div class="field-tip">建议填写你自己容易识别的工作空间名称，最多 100 个字符。</div>
            </el-form-item>
            <el-form-item label="管理员姓名">
              <el-input v-model="personalForm.admin_real_name" placeholder="请输入姓名" />
              <div class="field-tip">请输入真实姓名，方便后续识别管理员身份。</div>
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="personalForm.admin_phone" placeholder="请输入手机号" />
              <div class="field-tip">请输入 6 到 20 位数字。</div>
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="personalForm.admin_password" type="password" show-password />
              <div class="field-tip">密码至少 6 位，建议不要过于简单。</div>
            </el-form-item>
            <el-form-item label="租户编码">
              <el-input v-model="personalForm.tenant_code" placeholder="可选，不填则自动生成" />
              <div class="field-tip">可选。只能使用字母、数字和中划线，至少 3 个字符。</div>
            </el-form-item>
            <el-button class="login-button" type="primary" :loading="submitting" @click="handleCreatePersonal">
              创建并登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="创建机构" name="organization">
          <el-form class="login-form" :model="organizationForm">
            <el-form-item label="机构名称">
              <el-input v-model="organizationForm.name" placeholder="例如 测试律所" />
              <div class="field-tip">请输入律所或机构名称，最多 100 个字符。</div>
            </el-form-item>
            <el-form-item label="联系人">
              <el-input v-model="organizationForm.contact_name" placeholder="请输入联系人" />
              <div class="field-tip">用于后续机构联系和识别。</div>
            </el-form-item>
            <el-form-item label="管理员姓名">
              <el-input v-model="organizationForm.admin_real_name" placeholder="请输入管理员姓名" />
              <div class="field-tip">请输入机构管理员的真实姓名。</div>
            </el-form-item>
            <el-form-item label="管理员手机号">
              <el-input v-model="organizationForm.admin_phone" placeholder="请输入管理员手机号" />
              <div class="field-tip">请输入 6 到 20 位数字。</div>
            </el-form-item>
            <el-form-item label="管理员密码">
              <el-input v-model="organizationForm.admin_password" type="password" show-password />
              <div class="field-tip">密码至少 6 位。</div>
            </el-form-item>
            <el-form-item label="租户编码">
              <el-input v-model="organizationForm.tenant_code" placeholder="可选，不填则自动生成" />
              <div class="field-tip">可选。只能使用字母、数字和中划线，至少 3 个字符。</div>
            </el-form-item>
            <el-button class="login-button" type="primary" :loading="submitting" @click="handleCreateOrganization">
              创建机构并登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="加入机构" name="join">
          <el-form class="login-form" :model="joinForm">
            <el-form-item label="租户编码">
              <el-input v-model="joinForm.tenant_code" placeholder="请输入机构租户编码" />
              <div class="field-tip">请向机构管理员索取租户编码，例如 `test-lawfirm`。</div>
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="joinForm.real_name" placeholder="请输入姓名" />
              <div class="field-tip">请输入你的真实姓名，管理员审批时会看到。</div>
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="joinForm.phone" placeholder="请输入手机号" />
              <div class="field-tip">请输入 6 到 20 位数字。</div>
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="joinForm.password" type="password" show-password />
              <div class="field-tip">密码至少 6 位，审批通过后用它登录。</div>
            </el-form-item>
            <el-button class="login-button" type="primary" :loading="submitting" @click="handleJoinOrganization">
              提交加入申请
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-alert
        v-if="backendStatus"
        :title="backendStatus"
        :type="backendHealthy ? 'success' : 'warning'"
        show-icon
        :closable="false"
      />
      <el-alert v-if="successMessage" :title="successMessage" type="success" show-icon :closable="false" />
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

      <div class="login-hint">
        <span>默认管理员：</span>
        <code>13800000000 / admin123456</code>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '../stores/auth'
import http from '../lib/http'
import {
  extractFriendlyError,
  validateName,
  validatePassword,
  validatePhone,
  validateTenantCode,
  validateWorkspaceName,
} from '../lib/formMessages'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeTab = ref('login')
const loginForm = reactive({
  tenant_code: '',
  phone: '13800000000',
  password: 'admin123456',
})
const personalForm = reactive({
  workspace_name: '',
  admin_real_name: '',
  admin_phone: '',
  admin_password: '',
  tenant_code: '',
})
const organizationForm = reactive({
  name: '',
  contact_name: '',
  admin_real_name: '',
  admin_phone: '',
  admin_password: '',
  tenant_code: '',
})
const joinForm = reactive({
  tenant_code: '',
  real_name: '',
  phone: '',
  password: '',
})

const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const backendHealthy = ref(false)
const backendStatus = ref('')

onMounted(async () => {
  try {
    await authStore.checkBackendHealth()
    backendHealthy.value = true
    backendStatus.value = '后端服务连接正常'
  } catch {
    backendHealthy.value = false
    backendStatus.value = '后端服务未连接，请先启动 backend'
  }
})

function setMessages({ error = '', success = '' } = {}) {
  errorMessage.value = error
  successMessage.value = success
}

function resetForms() {
  personalForm.workspace_name = ''
  personalForm.admin_real_name = ''
  personalForm.admin_phone = ''
  personalForm.admin_password = ''
  personalForm.tenant_code = ''
  organizationForm.name = ''
  organizationForm.contact_name = ''
  organizationForm.admin_real_name = ''
  organizationForm.admin_phone = ''
  organizationForm.admin_password = ''
  organizationForm.tenant_code = ''
  joinForm.tenant_code = ''
  joinForm.real_name = ''
  joinForm.phone = ''
  joinForm.password = ''
}

function validateLoginForm() {
  return (
    validateTenantCode(loginForm.tenant_code) ||
    validatePhone(loginForm.phone) ||
    validatePassword(loginForm.password)
  )
}

function validatePersonalForm() {
  return (
    validateWorkspaceName(personalForm.workspace_name, '工作空间名称') ||
    validateName(personalForm.admin_real_name, '管理员姓名') ||
    validatePhone(personalForm.admin_phone, '管理员手机号') ||
    validatePassword(personalForm.admin_password, '管理员密码') ||
    validateTenantCode(personalForm.tenant_code)
  )
}

function validateOrganizationForm() {
  return (
    validateWorkspaceName(organizationForm.name, '机构名称') ||
    validateName(organizationForm.contact_name, '联系人') ||
    validateName(organizationForm.admin_real_name, '管理员姓名') ||
    validatePhone(organizationForm.admin_phone, '管理员手机号') ||
    validatePassword(organizationForm.admin_password, '管理员密码') ||
    validateTenantCode(organizationForm.tenant_code)
  )
}

function validateJoinForm() {
  return (
    validateTenantCode(joinForm.tenant_code, { required: true }) ||
    validateName(joinForm.real_name, '姓名') ||
    validatePhone(joinForm.phone) ||
    validatePassword(joinForm.password)
  )
}

async function handleLogin() {
  const validationMessage = validateLoginForm()
  if (validationMessage) {
    setMessages({ error: validationMessage })
    return
  }
  submitting.value = true
  setMessages()
  try {
    await authStore.login(loginForm)
    await router.push(route.query.redirect || '/')
  } catch (error) {
    if (axios.isAxiosError(error) && !error.response) {
      setMessages({ error: '无法连接后端服务，请先启动 backend。' })
    } else if (axios.isAxiosError(error) && error.response?.status === 401) {
      setMessages({ error: error.response.data?.detail || '账号或密码错误。' })
    } else {
      setMessages({ error: extractFriendlyError(error, '登录失败，请稍后重试。') })
    }
  } finally {
    submitting.value = false
  }
}

async function handleCreatePersonal() {
  const validationMessage = validatePersonalForm()
  if (validationMessage) {
    setMessages({ error: validationMessage })
    return
  }
  submitting.value = true
  setMessages()
  try {
    const { data } = await http.post('/tenants/personal', personalForm)
    await authStore.applyAccessToken(data.access_token)
    resetForms()
    ElMessage.success('个人空间创建成功')
    await router.push('/')
  } catch (error) {
    setMessages({ error: extractFriendlyError(error, '个人空间创建失败。') })
  } finally {
    submitting.value = false
  }
}

async function handleCreateOrganization() {
  const validationMessage = validateOrganizationForm()
  if (validationMessage) {
    setMessages({ error: validationMessage })
    return
  }
  submitting.value = true
  setMessages()
  try {
    const { data } = await http.post('/tenants/organization', organizationForm)
    await authStore.applyAccessToken(data.access_token)
    resetForms()
    ElMessage.success('机构创建成功')
    await router.push('/')
  } catch (error) {
    setMessages({ error: extractFriendlyError(error, '机构创建失败。') })
  } finally {
    submitting.value = false
  }
}

async function handleJoinOrganization() {
  const validationMessage = validateJoinForm()
  if (validationMessage) {
    setMessages({ error: validationMessage })
    return
  }
  submitting.value = true
  setMessages()
  try {
    const { data } = await http.post('/tenants/join', joinForm)
    loginForm.tenant_code = joinForm.tenant_code
    loginForm.phone = joinForm.phone
    loginForm.password = joinForm.password
    resetForms()
    activeTab.value = 'login'
    setMessages({ success: `${data.message} 当前状态：待审批。审批通过后再登录。` })
  } catch (error) {
    setMessages({ error: extractFriendlyError(error, '加入机构失败。') })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.field-tip {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}
</style>
