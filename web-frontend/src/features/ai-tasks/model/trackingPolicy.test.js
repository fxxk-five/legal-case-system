import { describe, expect, it } from 'vitest'

import {
  getAITaskStatusText,
  isAITaskFailed,
  isAITaskInFlight,
  isAITaskSucceeded,
  isAITaskTerminal,
  normalizeAITaskStatus,
  resolveAITaskStatusFromEvent,
} from './trackingPolicy'

describe('ai task tracking policy', () => {
  it('normalizes backend aliases to canonical statuses', () => {
    expect(normalizeAITaskStatus('queued')).toBe('pending')
    expect(normalizeAITaskStatus('running')).toBe('processing')
    expect(normalizeAITaskStatus('success')).toBe('completed')
    expect(normalizeAITaskStatus('error')).toBe('failed')
  })

  it('treats retrying as in-flight and dead as terminal failure', () => {
    expect(isAITaskInFlight('retrying')).toBe(true)
    expect(isAITaskFailed('dead')).toBe(true)
    expect(isAITaskTerminal('dead')).toBe(true)
    expect(isAITaskSucceeded('dead')).toBe(false)
  })

  it('resolves event status with payload status precedence', () => {
    expect(
      resolveAITaskStatusFromEvent({
        eventType: 'progress',
        eventStatus: 'retrying',
        progress: 0,
      }),
    ).toBe('retrying')

    expect(
      resolveAITaskStatusFromEvent({
        eventType: 'failed',
        eventStatus: 'dead',
        progress: 99,
      }),
    ).toBe('dead')
  })

  it('returns consistent status text labels', () => {
    expect(getAITaskStatusText('retrying')).toBe('重试中')
    expect(getAITaskStatusText('dead')).toBe('终止（死信）')
  })
})
