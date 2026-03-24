<template>
  <div class="p-5 rounded-2xl border border-border bg-white hover:shadow-apple-hover transition-all duration-300 group">
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-2.5">
        <div :class="[
          'p-2 rounded-xl shrink-0',
          typeStyles[fact.fact_type]?.bg || 'bg-gray-100 text-gray-600'
        ]">
          <component :is="typeStyles[fact.fact_type]?.icon || InfoIcon" class="w-4 h-4" />
        </div>
        <span class="text-xs font-semibold uppercase tracking-wide text-gray-500 readonly-field">
          {{ getTypeText(fact.fact_type) }}
        </span>
      </div>
      <span v-if="fact.occurrence_time" class="apple-badge apple-badge-neutral">
        {{ fact.occurrence_time }}
      </span>
    </div>

    <p class="text-sm leading-relaxed text-gray-700 font-medium readonly-field">
      {{ fact.description }}
    </p>

    <div v-if="fact.evidence_id" class="mt-5 pt-4 border-t border-gray-50 flex justify-end">
      <button class="text-xs font-bold text-[#007AFF] hover:opacity-80 transition-opacity flex items-center gap-1">
        查看关联证据 <ChevronRightIcon class="w-3 h-3" />
      </button>
    </div>
  </div>
</template>

<script setup>
import {
  UserIcon,
  ClockIcon,
  FileCheckIcon,
  ScaleIcon,
  InfoIcon,
  ChevronRightIcon
} from 'lucide-vue-next'

defineProps({
  fact: {
    type: Object,
    required: true,
  },
})

const typeStyles = {
  party: { bg: 'bg-blue-50 text-[#007AFF]', icon: UserIcon },
  timeline: { bg: 'bg-orange-50 text-[#FF9500]', icon: ClockIcon },
  evidence: { bg: 'bg-green-50 text-[#34C759]', icon: FileCheckIcon },
  law_reference: { bg: 'bg-red-50 text-[#FF3B30]', icon: ScaleIcon },
}

const getTypeText = (type) => {
  const texts = {
    party: '当事人',
    timeline: '时间线',
    evidence: '证据',
    law_reference: '法律条款',
  }
  return texts[type] || type
}
</script>
