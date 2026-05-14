import { computed, unref } from 'vue'

export const CASE_DETAIL_STATUS_OPTIONS = Object.freeze([
  Object.freeze({ value: 'new', label: '待上传材料' }),
  Object.freeze({ value: 'processing', label: '律师整理中' }),
  Object.freeze({ value: 'done', label: '分析完成' }),
])

function normalizeRouteCaseId(route, fallbackCaseId) {
  const routeCaseId = Number(route?.params?.id || 0)
  if (Number.isFinite(routeCaseId) && routeCaseId > 0) {
    return routeCaseId
  }

  const fallback = Number(unref(fallbackCaseId) || 0)
  return Number.isFinite(fallback) && fallback > 0 ? fallback : 0
}

function normalizeText(value) {
  return String(value === null || value === undefined ? '' : value).trim()
}

export function useCaseDetailOrchestration({
  route,
  router,
  caseId,
  caseDetail,
  caseCapabilities,
  invitePath,
} = {}) {
  const resolvedRoute = computed(() => unref(route) || {})
  const resolvedCaseDetail = computed(() => unref(caseDetail) || null)
  const resolvedCaseCapabilities = computed(() => unref(caseCapabilities) || {})
  const resolvedInvitePath = computed(() => normalizeText(unref(invitePath)))

  const fromClientDetail = computed(() => {
    const query = resolvedRoute.value?.query || {}
    return query.from === 'client' && Boolean(query.client_id)
  })

  const actionGuards = computed(() => {
    const actions = resolvedCaseCapabilities.value?.actions || {}
    return {
      canUpdateCaseStatus: Boolean(actions.canUpdateCaseStatus),
      canAccessAITasks: Boolean(actions.canAccessAITasks),
      canGenerateInvite: Boolean(actions.canGenerateInvite),
      canUploadFiles: Boolean(actions.canUploadFiles),
    }
  })

  const aiParsePath = computed(() => {
    const resolvedCaseId = normalizeRouteCaseId(resolvedRoute.value, caseId)
    return resolvedCaseId > 0 ? `/cases/${resolvedCaseId}/ai/parse` : '/cases'
  })

  const showInvitePath = computed(
    () => actionGuards.value.canGenerateInvite && Boolean(resolvedInvitePath.value),
  )

  const remarkCardVisible = computed(() => {
    const fields = resolvedCaseCapabilities.value?.fields || {}
    return Boolean(fields.canViewUploadGuide || fields.canViewClientRemark || fields.canViewLawyerRemark)
  })

  const canEditLawyerRemark = computed(() => {
    const fields = resolvedCaseCapabilities.value?.fields || {}
    return Boolean(fields.canEditLawyerRemark)
  })

  const remarkBlocks = computed(() => {
    const detail = resolvedCaseDetail.value || {}
    const fields = resolvedCaseCapabilities.value?.fields || {}
    const blocks = []

    const uploadGuide = normalizeText(detail.upload_guide)
    if (fields.canViewUploadGuide && uploadGuide) {
      blocks.push({
        key: 'upload_guide',
        label: '上传指引',
        content: uploadGuide,
        containerClass: 'rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4',
        labelClass: 'text-xs uppercase tracking-[0.18em] text-amber-700',
        contentClass: 'mt-2 whitespace-pre-wrap text-sm leading-6 text-amber-950',
      })
    }

    const clientRemark = normalizeText(detail.client_remark)
    if (fields.canViewClientRemark && clientRemark) {
      blocks.push({
        key: 'client_remark',
        label: '当事人补充说明',
        content: clientRemark,
        containerClass: 'rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-4',
        labelClass: 'text-xs uppercase tracking-[0.18em] text-slate-500',
        contentClass: 'mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-900',
      })
    }

    const lawyerRemark = normalizeText(detail.lawyer_remark)
    if (fields.canViewLawyerRemark && lawyerRemark && !fields.canEditLawyerRemark) {
      blocks.push({
        key: 'lawyer_remark',
        label: '律师内部备注',
        content: lawyerRemark,
        containerClass: 'rounded-2xl border border-cyan-100 bg-cyan-50 px-4 py-4',
        labelClass: 'text-xs uppercase tracking-[0.18em] text-cyan-700',
        contentClass: 'mt-2 whitespace-pre-wrap text-sm leading-6 text-cyan-950',
      })
    }

    return blocks
  })

  const showRemarkEmpty = computed(
    () => remarkCardVisible.value && remarkBlocks.value.length === 0 && !canEditLawyerRemark.value,
  )

  function goBack() {
    if (fromClientDetail.value) {
      return router.push({
        name: 'client-detail',
        params: { id: resolvedRoute.value?.query?.client_id },
      })
    }

    return router.push('/cases')
  }

  function goToAiParse() {
    if (!actionGuards.value.canAccessAITasks) {
      return false
    }

    router.push(aiParsePath.value)
    return true
  }

  return {
    actionGuards,
    aiParsePath,
    canEditLawyerRemark,
    fromClientDetail,
    goBack,
    goToAiParse,
    remarkBlocks,
    remarkCardVisible,
    showInvitePath,
    showRemarkEmpty,
    statusOptions: CASE_DETAIL_STATUS_OPTIONS,
  }
}
