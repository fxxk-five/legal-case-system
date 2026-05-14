import { describe, expect, it } from 'vitest'

import {
  buildCaseLongTaskCard,
  buildCaseTopFeedbackBanner,
  buildUploadFailureFeedback,
} from '../../../../../mini-program/features/cases/feedback.js'

describe('mini-program feedback builders', () => {
  it('builds warning banner for pending upload failures', () => {
    const banner = buildCaseTopFeedbackBanner({
      failedCount: 2,
      pendingQueueCount: 3,
      autoResumePending: false,
      canUploadFiles: true,
    })

    expect(banner?.tone).toBe('warning')
    expect(banner?.title).toContain('2')
    expect(banner?.actionLabel).toBe('继续上传')
  })

  it('builds info long-task card while analysis is processing', () => {
    const card = buildCaseLongTaskCard({
      caseInfo: {
        analysis_status: 'processing',
        analysis_progress: 42,
      },
      caseStage: {
        description: '材料已收到，律师正在整理。',
      },
      wsConnected: true,
    })

    expect(card).toBeTruthy()
    expect(card?.tone).toBe('info')
    expect(card?.progress).toBe(42)
    expect(card?.hint).toContain('实时通道已连接')
  })

  it('builds danger long-task card when analysis failed', () => {
    const card = buildCaseLongTaskCard({
      caseInfo: {
        analysis_status: 'failed',
        analysis_progress: 75,
      },
    })

    expect(card).toBeTruthy()
    expect(card?.tone).toBe('danger')
    expect(card?.actionLabel).toBe('刷新状态')
  })

  it('builds persistent upload failure feedback with resume message', () => {
    const feedback = buildUploadFailureFeedback({
      failedCount: 1,
      pendingQueueCount: 2,
      autoResumePending: true,
    })

    expect(feedback).toBeTruthy()
    expect(feedback?.title).toContain('1')
    expect(feedback?.message).toContain('网络恢复后会自动继续上传')
    expect(feedback?.actionLabel).toBe('继续上传 2 份')
  })
})
