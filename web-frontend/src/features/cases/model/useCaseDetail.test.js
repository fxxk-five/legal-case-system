import { ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { CASE_DETAIL_REFRESH_STRATEGY, useCaseDetail } from './useCaseDetail'

function buildCaseDetail(overrides = {}) {
  return {
    id: 7,
    title: 'Case Title',
    case_number: 'A-2026-0001',
    status: 'processing',
    analysis_status: 'processing',
    assigned_lawyer: { id: 8, real_name: 'Lawyer Zhang' },
    client: { id: 22, real_name: 'Client Li' },
    timeline: [
      {
        event_type: 'status_change',
        occurred_at: '2026-03-24T10:00:00',
        title: 'Status updated',
        description: 'Lawyer started organizing materials',
      },
    ],
    ...overrides,
  }
}

function buildFile(overrides = {}) {
  return {
    id: 101,
    file_name: 'evidence.pdf',
    file_type: 'application/pdf',
    can_download: true,
    uploader_role: 'lawyer',
    uploader_id: 8,
    uploader: { real_name: 'Lawyer Zhang' },
    description: 'Primary evidence',
    ...overrides,
  }
}

function createApiMocks() {
  return {
    fetchCaseDetailBundle: vi.fn(async () => ({
      caseDetail: buildCaseDetail(),
      files: [buildFile()],
    })),
    fetchCaseDetail: vi.fn(async () =>
      buildCaseDetail({
        status: 'done',
        analysis_status: 'completed',
      }),
    ),
    fetchCaseFiles: vi.fn(async () => [buildFile()]),
    updateCaseStatus: vi.fn(async () => ({})),
    uploadCaseFile: vi.fn(async () => ({ id: 303 })),
    downloadCaseFile: vi.fn(async () => true),
    deleteCaseFile: vi.fn(async () => ({})),
    fetchCaseInvitePath: vi.fn(async () => '/invite/demo-token'),
  }
}

function createNotifyMocks() {
  return {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }
}

describe('useCaseDetail', () => {
  it('loads the detail bundle and maps timeline/files through the controller', async () => {
    const api = createApiMocks()
    const notify = createNotifyMocks()

    const controller = useCaseDetail({
      caseId: ref(7),
      viewer: ref({ id: 8, role: 'lawyer' }),
      api,
      notify,
      confirmDelete: vi.fn(async () => true),
    })

    await controller.loadCase()

    expect(api.fetchCaseDetailBundle).toHaveBeenCalledWith(7)
    expect(controller.caseDetail.value.title).toBe('Case Title')
    expect(controller.statusForm.status).toBe('processing')
    expect(controller.timelineItems.value).toHaveLength(1)
    expect(controller.timelineItems.value[0].timelineKey).toContain('status_change')
    expect(controller.files.value).toHaveLength(1)
    expect(controller.files.value[0].capabilities.actions.canDownload).toBe(true)
    expect(controller.caseCapabilities.value.actions.canUpdateCaseStatus).toBe(true)
  })

  it('uses the documented refresh strategy for status, upload, and delete actions', async () => {
    const api = createApiMocks()
    const notify = createNotifyMocks()
    const confirmDelete = vi.fn(async () => true)

    const controller = useCaseDetail({
      caseId: ref(7),
      viewer: ref({ id: 8, role: 'lawyer' }),
      api,
      notify,
      confirmDelete,
    })

    expect(CASE_DETAIL_REFRESH_STRATEGY.statusUpdate).toBe('detail_and_files')
    expect(CASE_DETAIL_REFRESH_STRATEGY.uploadFile).toBe('detail_and_files')
    expect(CASE_DETAIL_REFRESH_STRATEGY.deleteFile).toBe('local_only')

    await controller.loadCase()
    controller.statusForm.status = 'done'

    await controller.updateStatus()
    expect(api.updateCaseStatus).toHaveBeenCalledWith(7, 'done')
    expect(api.fetchCaseDetail).toHaveBeenCalledTimes(1)
    expect(api.fetchCaseFiles).toHaveBeenCalledTimes(1)
    expect(api.fetchCaseDetailBundle).toHaveBeenCalledTimes(1)

    await controller.uploadFile({ name: 'new-evidence.pdf' })
    expect(api.uploadCaseFile).toHaveBeenCalledWith(7, { name: 'new-evidence.pdf' }, {})
    expect(api.fetchCaseDetailBundle).toHaveBeenCalledTimes(2)

    await controller.deleteFile({ id: 101, file_name: 'evidence.pdf' })
    expect(confirmDelete).toHaveBeenCalledTimes(1)
    expect(api.deleteCaseFile).toHaveBeenCalledWith(101)
    expect(api.fetchCaseDetailBundle).toHaveBeenCalledTimes(2)
    expect(controller.files.value).toHaveLength(0)
    expect(notify.success).toHaveBeenCalled()
  })

  it('guards invite generation for viewers without invite capability', async () => {
    const api = createApiMocks()
    const notify = createNotifyMocks()

    const controller = useCaseDetail({
      caseId: ref(7),
      viewer: ref({ id: 22, role: 'client' }),
      api,
      notify,
      confirmDelete: vi.fn(async () => true),
    })

    await controller.loadCase()
    const invitePath = await controller.loadInvitePath()

    expect(invitePath).toBe('')
    expect(api.fetchCaseInvitePath).not.toHaveBeenCalled()
    expect(notify.warning).toHaveBeenCalled()
  })
})
