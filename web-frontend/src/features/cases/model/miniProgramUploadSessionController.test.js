import { describe, expect, it, vi } from 'vitest'

import { createUploadSessionController } from '../../../../../mini-program/features/cases/upload-session-controller.js'

function buildLocalFile(name, size = 1024) {
  return {
    name,
    path: `/tmp/${name}`,
    size,
  }
}

describe('mini-program upload session controller', () => {
  it('filters invalid files and respects duplicate confirmation when appending', async () => {
    const controller = createUploadSessionController()
    const patches = []
    const onInvalidFiles = vi.fn(async () => {})
    const onConfirmDuplicates = vi.fn(async () => false)

    controller.setHandler((patch) => {
      patches.push(patch)
    })

    const result = await controller.appendFiles({
      files: [
        buildLocalFile('valid-a.pdf'),
        buildLocalFile('too-large.pdf', 25 * 1024 * 1024),
        { name: 'missing-path.pdf', size: 2048 },
        buildLocalFile('duplicate.pdf'),
      ],
      sourceText: 'local files',
      uploadedFiles: [{ file_name: 'duplicate.pdf', file_size: 1024 }],
      onInvalidFiles,
      onConfirmDuplicates,
    })

    expect(onInvalidFiles).toHaveBeenCalledTimes(1)
    expect(onConfirmDuplicates).toHaveBeenCalledTimes(1)
    expect(result.appendedCount).toBe(1)
    expect(controller.getState().selectedFiles).toHaveLength(1)
    expect(controller.getState().selectedFiles[0].name).toBe('valid-a.pdf')
    expect(patches.some((patch) => Array.isArray(patch.selectedFiles))).toBe(true)
  })

  it('keeps failed items in queue while removing successful uploads', async () => {
    const uploadedIds = []
    const controller = createUploadSessionController({
      uploadCaseFile: vi.fn(async ({ filePath }) => {
        if (filePath.includes('network-fail')) {
          throw { message: 'network timeout' }
        }
        return { id: 101, file_name: 'ok.pdf' }
      }),
    })

    await controller.appendFiles({
      files: [buildLocalFile('ok.pdf'), buildLocalFile('network-fail.pdf')],
      sourceText: 'local files',
    })

    const result = await controller.continuePendingUploads({
      caseId: 7,
      canUploadFiles: true,
      networkOnline: true,
      skipConfirm: true,
      onFileUploaded: async (uploaded) => {
        uploadedIds.push(uploaded.id)
      },
    })

    expect(result.started).toBe(true)
    expect(result.successCount).toBe(1)
    expect(result.remainingCount).toBe(1)
    expect(result.autoResumePending).toBe(false)
    expect(result.networkNoticeText).toBe('')
    expect(uploadedIds).toEqual([101])
    expect(controller.getState().selectedFiles).toHaveLength(1)
    expect(controller.getState().selectedFiles[0].name).toBe('network-fail.pdf')
    expect(controller.getState().selectedFiles[0].status).toBe('failed')
    expect(controller.getState().uploadSessionNotice).toContain('1')
  })
})
