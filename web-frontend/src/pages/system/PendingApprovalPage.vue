<template>
  <div class="mx-auto max-w-3xl">
    <div class="bento-card py-14 text-center space-y-4">
      <Clock3Icon class="w-12 h-12 mx-auto text-amber-500" />
      <h2 class="text-3xl font-bold tracking-tight">账号待审批</h2>
      <p class="text-muted-foreground leading-relaxed">
        当前账号已完成注册，但尚未被机构管理员审批通过。审批完成后可访问概览、案件、当事人与分析模块。
      </p>
      <p class="text-sm text-muted-foreground">
        如长时间未生效，请联系机构管理员处理。
      </p>
    </div>
  </div>
</template>

<script setup>
import { Clock3Icon } from 'lucide-vue-next'
</script>
