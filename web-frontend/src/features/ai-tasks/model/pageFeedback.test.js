import { describe, expect, it } from 'vitest'

import {
  clearAITaskFeedbackHint,
  loadAITaskFeedbackHint,
  saveAITaskFeedbackHint,
} from './pageFeedback'

function createMemoryStorage() {
  const store = new Map()
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
  }
}

describe('ai task page feedback hint', () => {
  it('saves and loads task id by case and task type', () => {
    const storage = createMemoryStorage()

    const saved = saveAITaskFeedbackHint({
      caseId: 7,
      taskType: 'analyze',
      taskId: 'task-123',
      storage,
    })
    const loaded = loadAITaskFeedbackHint({
      caseId: 7,
      taskType: 'analyze',
      storage,
    })

    expect(saved).toBe(true)
    expect(loaded).toBe('task-123')
  })

  it('clears saved task id by case and task type', () => {
    const storage = createMemoryStorage()

    saveAITaskFeedbackHint({
      caseId: 9,
      taskType: 'falsify',
      taskId: 'task-to-remove',
      storage,
    })

    expect(clearAITaskFeedbackHint({ caseId: 9, taskType: 'falsify', storage })).toBe(true)
    expect(loadAITaskFeedbackHint({ caseId: 9, taskType: 'falsify', storage })).toBe('')
  })

  it('ignores invalid case/task input', () => {
    const storage = createMemoryStorage()

    expect(
      saveAITaskFeedbackHint({
        caseId: 0,
        taskType: '',
        taskId: 'task-1',
        storage,
      }),
    ).toBe(false)
    expect(loadAITaskFeedbackHint({ caseId: 0, taskType: '', storage })).toBe('')
    expect(clearAITaskFeedbackHint({ caseId: 0, taskType: '', storage })).toBe(false)
  })
})
