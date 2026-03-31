<template>
  <div class="mx-auto max-w-3xl">
    <div class="bento-card py-14 text-center space-y-4">
      <ShieldAlertIcon class="w-12 h-12 mx-auto text-rose-500" />
      <h2 class="text-3xl font-bold tracking-tight">访问受限</h2>
      <p class="text-muted-foreground leading-relaxed">
        当前账号角色暂未开放 Web 端完整功能菜单。请联系管理员确认账号角色与权限范围。
      </p>
      <RouterLink
        to="/login"
        class="inline-flex items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-apple transition-all hover:bg-primary/90"
      >
        返回登录页
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { ShieldAlertIcon } from 'lucide-vue-next'
</script>
