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
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

async function handleSubmit() {
  submitting.value = true
  errorMessage.value = ''
  try {
    await authStore.login(form)
    await router.push(route.query.redirect || '/')
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '登录失败，请检查账号密码。'
  } finally {
    submitting.value = false
  }
}
</script>
