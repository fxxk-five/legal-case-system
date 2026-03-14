<template>
  <section class="login-page">
    <div class="login-panel">
      <div class="login-copy">
        <p class="eyebrow">LEGAL CASE SYSTEM</p>
        <h1>律所案件管理后台</h1>
        <p>先完成管理员与律师的日常工作流，再逐步扩展到当事人协同和小程序端。</p>
      </div>

      <el-form class="login-form" :model="form" @submit.prevent="handleSubmit">
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-alert
          v-if="backendStatus"
          :title="backendStatus"
          :type="backendHealthy ? 'success' : 'warning'"
          show-icon
          :closable="false"
        />
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />
        <el-button class="login-button" type="primary" :loading="submitting" @click="handleSubmit">
          登录
        </el-button>
      </el-form>

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

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({
  phone: '13800000000',
  password: 'admin123456',
})

const submitting = ref(false)
const errorMessage = ref('')
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

async function handleSubmit() {
  submitting.value = true
  errorMessage.value = ''
  try {
    await authStore.login(form)
    await router.push(route.query.redirect || '/')
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        errorMessage.value = '无法连接后端服务，请先启动 backend。'
      } else if (error.response.status === 401) {
        errorMessage.value = error.response.data?.detail || '账号或密码错误。'
      } else {
        errorMessage.value = error.response.data?.detail || '登录失败，请检查后端接口。'
      }
    } else {
      errorMessage.value = '登录失败，请稍后重试。'
    }
  } finally {
    submitting.value = false
  }
}
</script>
