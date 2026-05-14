import { describe, expect, it } from 'vitest'

import {
  CASE_CAPABILITY_ACTION_KEYS,
  CASE_CAPABILITY_FIELD_KEYS,
  CASE_FILE_CAPABILITY_ACTION_KEYS,
  CASE_FILE_CAPABILITY_FIELD_KEYS,
  CASE_POLICY_CONTRACT_VERSION,
  CASE_STAGE_IDS,
  buildCaseCapabilities,
  buildCaseFileCapabilities,
  caseStageMap,
  getCaseStageBadgeClass,
  getCaseStageReminderLevel,
  isCaseAnalysisInProgress,
  resolveCaseStage,
} from './policy'

describe('resolveCaseStage', () => {
  it('maps a new case to awaiting materials', () => {
    const stage = resolveCaseStage({
      status: 'new',
      analysis_status: 'not_started',
    })

    expect(stage.id).toBe(caseStageMap.awaiting_materials.id)
    expect(stage.label).toBe('待上传材料')
    expect(stage.primaryAction.label).toBe('补充材料')
    expect(stage.locked).toBe(false)
    expect(stage.showAIResult).toBe(false)
  })

  it('maps queued and reanalysis states to reviewing materials', () => {
    const stage = resolveCaseStage({
      status: 'processing',
      analysis_status: 'pending_reanalysis',
    })

    expect(stage.id).toBe(caseStageMap.reviewing_materials.id)
    expect(stage.label).toBe('律师整理中')
    expect(stage.locked).toBe(true)
    expect(stage.description).toContain('重新解析')
  })

  it('maps completed analysis to completed stage', () => {
    const stage = resolveCaseStage({
      status: 'processing',
      analysis_status: 'completed',
    })

    expect(stage.id).toBe(caseStageMap.analysis_completed.id)
    expect(stage.showAIResult).toBe(true)
    expect(stage.primaryAction.key).toBe('view_results')
  })

  it('maps failed analysis to attention needed', () => {
    const stage = resolveCaseStage({
      status: 'processing',
      analysis_status: 'failed',
    })

    expect(stage.id).toBe(caseStageMap.attention_needed.id)
    expect(stage.locked).toBe(false)
    expect(stage.tone).toBe('danger')
  })

  it('uses upload session states as stage overrides', () => {
    const stage = resolveCaseStage(
      {
        status: 'processing',
        analysis_status: 'queued',
      },
      {
        uploadingCount: 2,
      },
    )

    expect(stage.id).toBe(caseStageMap.uploading_materials.id)
    expect(stage.description).toContain('2 份材料')
    expect(stage.locked).toBe(true)
  })

  it('marks pending local files before submission as awaiting materials', () => {
    const stage = resolveCaseStage(
      {
        status: 'processing',
        analysis_status: 'queued',
      },
      {
        pendingUploads: 3,
      },
    )

    expect(stage.id).toBe(caseStageMap.awaiting_materials.id)
    expect(stage.listHint).toBe('3 份待上传')
  })
})

describe('case stage helpers', () => {
  it('returns badge and reminder classes from stage tone', () => {
    const stage = resolveCaseStage({
      status: 'done',
      analysis_status: 'completed',
    })

    expect(getCaseStageBadgeClass(stage)).toBe('apple-badge-success')
    expect(getCaseStageReminderLevel(stage)).toBe('success')
  })

  it('tracks analysis progress states centrally', () => {
    expect(isCaseAnalysisInProgress('queued')).toBe(true)
    expect(isCaseAnalysisInProgress('processing')).toBe(true)
    expect(isCaseAnalysisInProgress('completed')).toBe(false)
  })
})

describe('case policy contract', () => {
  it('keeps the agreed contract keys stable', () => {
    expect(CASE_POLICY_CONTRACT_VERSION).toBe('2026-03-25-v1')
    expect(CASE_STAGE_IDS).toEqual([
      'awaiting_materials',
      'uploading_materials',
      'upload_attention',
      'reviewing_materials',
      'analysis_completed',
      'attention_needed',
    ])
    expect(CASE_CAPABILITY_FIELD_KEYS).toEqual([
      'canViewLawyerRemark',
      'canViewClientRemark',
      'canViewUploadGuide',
      'canViewInternalFileDescription',
      'canViewOwnFileDescription',
    ])
    expect(CASE_CAPABILITY_ACTION_KEYS).toEqual([
      'canUploadFiles',
      'canDeleteAnyFile',
      'canDeleteOwnFile',
      'canDownloadAllFiles',
      'canDownloadOwnFiles',
      'canEditClientRemark',
      'canEditLawyerRemark',
      'canUpdateCaseStatus',
      'canEditUploadGuide',
      'canViewAIResults',
      'canAccessAITasks',
      'canDownloadLatestReport',
      'canGenerateInvite',
    ])
    expect(CASE_FILE_CAPABILITY_FIELD_KEYS).toEqual(['canViewDescription'])
    expect(CASE_FILE_CAPABILITY_ACTION_KEYS).toEqual(['canDownload', 'canDelete'])
  })
})

describe('case capabilities', () => {
  const lawyerViewer = {
    id: 8,
    role: 'lawyer',
    is_tenant_admin: false,
  }

  const clientViewer = {
    id: 22,
    role: 'client',
    is_tenant_admin: false,
  }

  const editorCase = {
    assigned_lawyer: { id: 8 },
    client: { id: 22 },
    analysis_status: 'processing',
    status: 'processing',
  }

  it('allows the case editor to view and edit lawyer-only fields', () => {
    const capabilities = buildCaseCapabilities({
      viewer: lawyerViewer,
      caseItem: editorCase,
    })

    expect(capabilities.fields.canViewLawyerRemark).toBe(true)
    expect(capabilities.actions.canEditLawyerRemark).toBe(true)
    expect(capabilities.actions.canUpdateCaseStatus).toBe(true)
    expect(capabilities.actions.canAccessAITasks).toBe(true)
  })

  it('limits the client viewer to own remarks and files', () => {
    const capabilities = buildCaseCapabilities({
      viewer: clientViewer,
      caseItem: editorCase,
    })

    expect(capabilities.fields.canViewLawyerRemark).toBe(false)
    expect(capabilities.fields.canViewClientRemark).toBe(true)
    expect(capabilities.actions.canEditClientRemark).toBe(true)
    expect(capabilities.actions.canEditLawyerRemark).toBe(false)
    expect(capabilities.actions.canDownloadAllFiles).toBe(false)
  })

  it('builds file capabilities from the central rules', () => {
    const capabilities = buildCaseCapabilities({
      viewer: clientViewer,
      caseItem: editorCase,
    })

    const ownFileCapabilities = buildCaseFileCapabilities({
      viewer: clientViewer,
      caseItem: editorCase,
      fileItem: {
        uploader_role: 'client',
        uploader_id: 22,
        can_download: true,
        description: '当事人补充说明',
      },
      caseCapabilities: capabilities,
    })

    const lawyerFileCapabilities = buildCaseFileCapabilities({
      viewer: clientViewer,
      caseItem: editorCase,
      fileItem: {
        uploader_role: 'lawyer',
        uploader_id: 8,
        can_download: false,
        description: '律师内部说明',
      },
      caseCapabilities: capabilities,
    })

    expect(ownFileCapabilities.actions.canDownload).toBe(true)
    expect(ownFileCapabilities.actions.canDelete).toBe(true)
    expect(ownFileCapabilities.fields.canViewDescription).toBe(true)
    expect(lawyerFileCapabilities.actions.canDownload).toBe(false)
    expect(lawyerFileCapabilities.fields.canViewDescription).toBe(false)
  })
})
