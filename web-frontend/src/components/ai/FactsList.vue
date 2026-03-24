<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">案件事实</h3>
      <el-select
        v-model="selectedType"
        placeholder="筛选类型"
        clearable
        class="apple-select w-40"
      >
        <el-option label="全部" value="" />
        <el-option label="当事人信息" value="party" />
        <el-option label="时间线" value="timeline" />
        <el-option label="证据" value="evidence" />
        <el-option label="法律条款" value="law_reference" />
      </el-select>
    </div>

    <el-empty v-if="facts.length === 0" description="暂无事实数据" :image-size="80" />

    <div v-else class="grid grid-cols-1 gap-4">
      <fact-card
        v-for="fact in filteredFacts"
        :key="fact.id"
        :fact="fact"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import FactCard from './FactCard.vue'

const props = defineProps({
  facts: {
    type: Array,
    required: true,
  },
})

const selectedType = ref('')

const filteredFacts = computed(() => {
  if (!selectedType.value) {
    return props.facts
  }
  return props.facts.filter(fact => fact.fact_type === selectedType.value)
})
</script>
