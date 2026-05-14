import { describe, expect, it, vi } from 'vitest'

import {
  clearPageTaskFeedback,
  createAITaskTracker,
  getTaskStatusText,
  loadPageTaskFeedback,
  normalizeTask,
  savePageTaskFeedback,
} from '../../../../../mini-program/features/ai/aiTask.js'

const TASK_ID = '11111111-1111-4111-8111-111111111111'

describe('mini-program ai task tracking', () => {
  it('maps retrying and dead status texts', () => {
    expect(getTaskStatusText('retrying')).toBe('重试中')
    expect(getTaskStatusText('dead')).toBe('终止（死信）')
  })

  it('keeps dead status as terminal in normalizeTask output', () => {
    const normalized = normalizeTask({
      task_id: TASK_ID,
      status: 'dead',
      progress: 120,
      message: 'Task moved to dead-letter',
    })

    expect(normalized.status).toBe('dead')
    expect(normalized.progress).toBe(100)
  })

  it('stops tracker when polled task enters dead status', async () => {
    const previousUni = globalThis.uni
    globalThis.uni = {
      getStorageSync() {
        return ''
      },
      connectSocket() {
        return {
          onOpen() {},
          onMessage() {},
          onError() {},
          onClose() {},
          close() {},
        }
      },
    }

    try {
      const onFailed = vi.fn()
      const getTaskStatus = vi.fn(async () => ({
        task_id: TASK_ID,
        status: 'dead',
        progress: 100,
        message: 'Task moved to dead-letter',
        error_message: 'Task moved to dead-letter state after max retries.',
      }))

      const tracker = createAITaskTracker({
        getTaskStatus,
        pollIntervalMs: 20,
        onFailed,
        reconnectDelays: [5],
      })

      tracker.start({
        task_id: TASK_ID,
        status: 'processing',
        progress: 35,
        message: '执行中',
      })

      await new Promise((resolve) => setTimeout(resolve, 60))

      expect(onFailed).toHaveBeenCalledTimes(1)
      expect(tracker.getCurrentTask()?.status).toBe('dead')
      expect(getTaskStatus).toHaveBeenCalledTimes(1)
    } finally {
      globalThis.uni = previousUni
    }
  })

  it('persists and restores page feedback by case and task type', () => {
    const previousUni = globalThis.uni
    const storage = new Map()
    globalThis.uni = {
      setStorageSync(key, value) {
        storage.set(key, value)
      },
      getStorageSync(key) {
        return storage.get(key)
      },
      removeStorageSync(key) {
        storage.delete(key)
      },
    }

    try {
      const saved = savePageTaskFeedback({
        caseId: 3,
        taskType: 'parse',
        task: {
          task_id: TASK_ID,
          status: 'running',
          progress: 45,
          message: 'processing',
        },
      })
      expect(saved).toBe(true)

      const loaded = loadPageTaskFeedback({
        caseId: 3,
        taskType: 'parse',
      })
      expect(loaded?.task_id).toBe(TASK_ID)
      expect(loaded?.status).toBe('processing')
      expect(loaded?.progress).toBe(45)

      const mismatch = loadPageTaskFeedback({
        caseId: 3,
        taskType: 'analyze',
      })
      expect(mismatch).toBeNull()

      const cleared = clearPageTaskFeedback({
        caseId: 3,
        taskType: 'parse',
      })
      expect(cleared).toBe(true)
      expect(
        loadPageTaskFeedback({
          caseId: 3,
          taskType: 'parse',
        }),
      ).toBeNull()
    } finally {
      globalThis.uni = previousUni
    }
  })
})
