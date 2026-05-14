import { describe, expect, it } from 'vitest'

import {
  CASE_POLICY_CONTRACT_VERSION as webPolicyVersion,
  CASE_STAGE_IDS as webStageIds,
  caseStageMap as webCaseStageMap,
  resolveCaseStage as resolveWebCaseStage,
} from '../../../entities/case/model/policy'
import {
  getAITaskStatusText,
  normalizeAITaskStatus,
} from '../../ai-tasks/model/trackingPolicy'
import {
  CASE_POLICY_CONTRACT_VERSION as miniPolicyVersion,
  CASE_STAGE_IDS as miniStageIds,
  caseStageMap as miniCaseStageMap,
  resolveCaseStage as resolveMiniCaseStage,
} from '../../../../../mini-program/entities/case/policy.js'
import {
  getTaskStatusText as getMiniTaskStatusText,
  normalizeTask as normalizeMiniTask,
} from '../../../../../mini-program/features/ai/aiTask.js'

function pickStageTextContract(stage) {
  return {
    label: stage.label,
    description: stage.description,
    listHint: stage.listHint,
    tone: stage.tone,
    locked: stage.locked,
    showAIResult: stage.showAIResult,
    primaryAction: {
      key: stage.primaryAction?.key || '',
      label: stage.primaryAction?.label || '',
    },
  }
}

function normalizeMiniTaskStatus(status) {
  return normalizeMiniTask({
    task_id: 'mini-parity-task',
    status,
    progress: 0,
  }).status
}

describe('dual-end status parity', () => {
  it('keeps case stage base copy identical between web and mini', () => {
    expect(webPolicyVersion).toBe(miniPolicyVersion)
    expect(webStageIds).toEqual(miniStageIds)

    expect(
      webStageIds.map((stageId) => [stageId, pickStageTextContract(webCaseStageMap[stageId])]),
    ).toEqual(
      miniStageIds.map((stageId) => [stageId, pickStageTextContract(miniCaseStageMap[stageId])]),
    )
  })

  it('resolves case stage copy identically for the same scenarios', () => {
    const scenarios = [
      {
        key: 'new',
        caseItem: { status: 'new', analysis_status: 'not_started' },
        options: {},
      },
      {
        key: 'pending-reanalysis',
        caseItem: { status: 'processing', analysis_status: 'pending_reanalysis' },
        options: {},
      },
      {
        key: 'processing',
        caseItem: { status: 'processing', analysis_status: 'processing' },
        options: {},
      },
      {
        key: 'failed',
        caseItem: { status: 'processing', analysis_status: 'failed' },
        options: {},
      },
      {
        key: 'completed',
        caseItem: { status: 'done', analysis_status: 'completed' },
        options: {},
      },
      {
        key: 'uploading',
        caseItem: { status: 'processing', analysis_status: 'queued' },
        options: { uploadingCount: 2 },
      },
      {
        key: 'failed-uploads',
        caseItem: { status: 'processing', analysis_status: 'queued' },
        options: { failedUploads: 1 },
      },
      {
        key: 'pending-uploads',
        caseItem: { status: 'processing', analysis_status: 'queued' },
        options: { pendingUploads: 3 },
      },
    ]

    expect(
      scenarios.map(({ key, caseItem, options }) => [
        key,
        pickStageTextContract(resolveWebCaseStage(caseItem, options)),
      ]),
    ).toEqual(
      scenarios.map(({ key, caseItem, options }) => [
        key,
        pickStageTextContract(resolveMiniCaseStage(caseItem, options)),
      ]),
    )
  })

  it('keeps AI task status normalization and labels identical between web and mini', () => {
    const statuses = [
      '',
      'pending',
      'queued',
      'processing',
      'running',
      'retrying',
      'completed',
      'success',
      'failed',
      'error',
      'dead',
      'unknown',
    ]

    expect(
      statuses.map((status) => ({
        status,
        normalized: normalizeAITaskStatus(status),
        text: getAITaskStatusText(status),
      })),
    ).toEqual(
      statuses.map((status) => ({
        status,
        normalized: normalizeMiniTaskStatus(status),
        text: getMiniTaskStatusText(status),
      })),
    )
  })
})
