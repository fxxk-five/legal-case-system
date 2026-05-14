import { describe, expect, it } from 'vitest'

import {
  createClientCaseDetailController,
  createLawyerCaseDetailController,
} from '../../../../../mini-program/features/cases/detail-controller.js'

const TASK_ID = '11111111-1111-4111-8111-111111111111'

function buildClientDetail(analysisStatus, overrides = {}) {
  return {
    id: 7,
    title: '案件详情',
    status: analysisStatus === 'completed' ? 'done' : 'processing',
    analysis_status: analysisStatus,
    analysis_progress: analysisStatus === 'completed' ? 100 : 18,
    timeline: [
      {
        title: 'AI 分析启动',
        description: `任务 ${TASK_ID} 已创建`,
        occurred_at: '2026-03-24T10:00:00Z',
        operator_name: '张三',
      },
    ],
    client: {
      id: 99,
      real_name: '张三',
    },
    ...overrides,
  }
}

describe('mini-program detail controllers', () => {
  it('keeps the registered client state handler during tracker-driven reload', async () => {
    let detailCallCount = 0
    const patches = []
    const startedTasks = []

    const controller = createClientCaseDetailController({
      getCases: async () => [{ id: 7 }],
      getCaseDetail: async () => {
        detailCallCount += 1
        return detailCallCount === 1 ? buildClientDetail('processing') : buildClientDetail('completed')
      },
      getCaseFiles: async () => [],
      getAnalysisResults: async () => ({
        items: [
          {
            summary: '分析完成',
            weaknesses: ['补充证据'],
            recommendations: ['补充证据'],
          },
        ],
      }),
      getTaskStatus: async () => ({
        task_id: TASK_ID,
        status: 'completed',
        progress: 100,
        message: '分析完成',
      }),
      createTracker: (options = {}) => ({
        start(task) {
          startedTasks.push(task)
          queueMicrotask(() => {
            options.onCompleted?.({
              ...task,
              status: 'completed',
              progress: 100,
              message: '分析完成',
            })
          })
          return task
        },
        stop() {},
        replaceTask(task) {
          return task
        },
        getCurrentTask() {
          return startedTasks[startedTasks.length - 1] || null
        },
        pullTaskStatus() {
          return null
        },
      }),
    })

    await controller.load({
      preferredCaseId: 7,
      viewer: { id: 99, role: 'client' },
      onStateChange: (patch, currentState) => {
        patches.push({ patch, currentState })
      },
    })

    await new Promise((resolve) => setTimeout(resolve, 20))

    expect(startedTasks).toHaveLength(1)
    expect(detailCallCount).toBeGreaterThanOrEqual(2)

    const completedState = patches.find((entry) => entry.currentState?.caseInfo?.analysis_status === 'completed')
    expect(completedState).toBeTruthy()
    expect(completedState.currentState.latestAnalysis?.summary).toBe('分析完成')
    expect(completedState.currentState.missingEvidenceHints).toEqual(['补充证据'])

    controller.dispose()
  })

  it('returns a mapped lawyer case snapshot', async () => {
    const controller = createLawyerCaseDetailController({
      getCaseDetail: async () => ({
        id: 12,
        title: '律师案件详情',
        status: 'done',
        analysis_status: 'completed',
        timeline: [],
        client: {
          id: 66,
          real_name: '李四',
        },
      }),
      getCaseFiles: async () => [
        {
          id: 3,
          file_name: 'evidence.pdf',
          can_download: true,
          uploader_role: 'lawyer',
          uploader_id: 8,
        },
      ],
    })

    const snapshot = await controller.load({
      caseId: 12,
      viewer: { id: 8, role: 'lawyer' },
    })

    expect(snapshot.caseId).toBe(12)
    expect(snapshot.caseStage.id).toBe('analysis_completed')
    expect(snapshot.caseCapabilities.actions.canGenerateInvite).toBe(true)
    expect(snapshot.files).toHaveLength(1)
    expect(snapshot.files[0].capabilities.actions.canDownload).toBe(true)
  })
})
