import { reactive, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import {
  CASE_DETAIL_STATUS_OPTIONS,
  useCaseDetailOrchestration,
} from './useCaseDetailOrchestration'

function createOrchestrationContext(overrides = {}) {
  const route = reactive({
    params: { id: '7' },
    query: {},
    ...(overrides.route || {}),
  })

  return {
    route,
    router: overrides.router || { push: vi.fn() },
    caseId: overrides.caseId || ref(7),
    caseDetail:
      overrides.caseDetail ||
      ref({
        upload_guide: '',
        client_remark: '',
        lawyer_remark: '',
      }),
    caseCapabilities:
      overrides.caseCapabilities ||
      ref({
        fields: {
          canViewUploadGuide: false,
          canViewClientRemark: false,
          canViewLawyerRemark: false,
        },
        actions: {
          canUpdateCaseStatus: false,
          canAccessAITasks: false,
          canGenerateInvite: false,
          canUploadFiles: false,
        },
      }),
    invitePath: overrides.invitePath || ref(''),
  }
}

describe('useCaseDetailOrchestration', () => {
  it('routes back to client detail when opened from client page', () => {
    const router = { push: vi.fn() }
    const context = createOrchestrationContext({
      router,
      route: {
        query: {
          from: 'client',
          client_id: '22',
        },
      },
    })

    const orchestration = useCaseDetailOrchestration(context)
    orchestration.goBack()

    expect(orchestration.fromClientDetail.value).toBe(true)
    expect(router.push).toHaveBeenCalledWith({
      name: 'client-detail',
      params: { id: '22' },
    })
  })

  it('builds action guards and ai parse navigation from capabilities', () => {
    const router = { push: vi.fn() }
    const caseCapabilities = ref({
      fields: {},
      actions: {
        canUpdateCaseStatus: true,
        canAccessAITasks: true,
        canGenerateInvite: true,
        canUploadFiles: true,
      },
    })

    const orchestration = useCaseDetailOrchestration(
      createOrchestrationContext({
        router,
        caseCapabilities,
      }),
    )

    expect(orchestration.actionGuards.value).toEqual({
      canUpdateCaseStatus: true,
      canAccessAITasks: true,
      canGenerateInvite: true,
      canUploadFiles: true,
    })
    expect(orchestration.aiParsePath.value).toBe('/cases/7/ai/parse')
    expect(orchestration.goToAiParse()).toBe(true)
    expect(router.push).toHaveBeenCalledWith('/cases/7/ai/parse')
  })

  it('maps remark blocks from capability and content visibility', () => {
    const caseCapabilities = ref({
      fields: {
        canViewUploadGuide: true,
        canViewClientRemark: true,
        canViewLawyerRemark: false,
      },
      actions: {},
    })
    const caseDetail = ref({
      upload_guide: '请先上传身份证与合同',
      client_remark: '我补充了一份聊天记录',
      lawyer_remark: '内部备注不可见',
    })

    const orchestration = useCaseDetailOrchestration(
      createOrchestrationContext({
        caseCapabilities,
        caseDetail,
      }),
    )

    expect(orchestration.remarkCardVisible.value).toBe(true)
    expect(orchestration.remarkBlocks.value.map((item) => item.key)).toEqual([
      'upload_guide',
      'client_remark',
    ])

    caseDetail.value = {
      upload_guide: '',
      client_remark: '',
      lawyer_remark: '',
    }
    expect(orchestration.showRemarkEmpty.value).toBe(true)
  })

  it('keeps invite visibility controlled by action and non-empty path', () => {
    const caseCapabilities = ref({
      fields: {},
      actions: {
        canGenerateInvite: true,
      },
    })
    const invitePath = ref('/invite/demo-token')

    const orchestration = useCaseDetailOrchestration(
      createOrchestrationContext({
        caseCapabilities,
        invitePath,
      }),
    )

    expect(CASE_DETAIL_STATUS_OPTIONS.map((item) => item.value)).toEqual(['new', 'processing', 'done'])
    expect(orchestration.showInvitePath.value).toBe(true)

    invitePath.value = ''
    expect(orchestration.showInvitePath.value).toBe(false)
  })
})
