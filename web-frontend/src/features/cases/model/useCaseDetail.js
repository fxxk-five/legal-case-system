import { computed, reactive, ref, unref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { ElMessageBox } from 'element-plus/es/components/message-box/index'

import { extractFriendlyError } from '../../../shared/lib/formMessages'
import * as casesApi from '../api/index'
import { mapCaseFileItems, mapCaseTimelineItems } from '../../../entities/case/model/mapper'
import { buildCaseCapabilities, resolveCaseStage } from '../../../entities/case/model/policy'

function createNotifier(notify) {
  return {
    success(message) {
      notify?.success?.(message)
    },
    error(message) {
      notify?.error?.(message)
    },
    warning(message) {
      notify?.warning?.(message)
    },
  }
}

function normalizeCaseId(caseId) {
  const parsed = Number(unref(caseId) || 0)
  return Number.isFinite(parsed) ? parsed : 0
}

function isCancelError(error) {
  return error === 'cancel' || error === 'close'
}

export const CASE_DETAIL_REFRESH_STRATEGY = Object.freeze({
  initialLoad: 'detail_and_files',
  statusUpdate: 'detail_and_files',
  uploadFile: 'detail_and_files',
  deleteFile: 'local_only',
  invitePath: 'local_only',
  downloadFile: 'none',
})

export function useCaseDetail({
  caseId,
  viewer,
  api = casesApi,
  notify = ElMessage,
  confirmDelete = (...args) => ElMessageBox.confirm(...args),
} = {}) {
  const notifier = createNotifier(notify)

  const caseDetail = ref(null)
  const rawFiles = ref([])
  const invitePath = ref('')
  const loading = ref(false)
  const loadingFiles = ref(false)

  const statusForm = reactive({
    status: '',
  })

  const resolvedViewer = computed(() => unref(viewer) || null)
  const caseStage = computed(() =>
    resolveCaseStage(caseDetail.value, { hasUploadedFiles: rawFiles.value.length > 0 }),
  )
  const caseCapabilities = computed(() =>
    buildCaseCapabilities({
      viewer: resolvedViewer.value,
      caseItem: caseDetail.value,
      stage: caseStage.value,
    }),
  )
  const files = computed(() =>
    mapCaseFileItems(rawFiles.value, {
      viewer: resolvedViewer.value,
      caseItem: caseDetail.value,
      caseCapabilities: caseCapabilities.value,
    }),
  )
  const timelineItems = computed(() => mapCaseTimelineItems(caseDetail.value?.timeline))

  async function loadCase({ silent = false } = {}) {
    const targetCaseId = normalizeCaseId(caseId)
    if (!targetCaseId) {
      caseDetail.value = null
      rawFiles.value = []
      statusForm.status = ''
      invitePath.value = ''
      loadingFiles.value = false
      return null
    }

    loading.value = true
    loadingFiles.value = true
    invitePath.value = ''

    try {
      const bundle = await api.fetchCaseDetailBundle(targetCaseId)
      caseDetail.value = bundle.caseDetail
      rawFiles.value = Array.isArray(bundle.files) ? bundle.files : []
      statusForm.status = bundle.caseDetail?.status || ''
      return bundle
    } catch (error) {
      if (!silent) {
        notifier.error(extractFriendlyError(error, '案件详情加载失败。'))
      }
      return null
    } finally {
      loading.value = false
      loadingFiles.value = false
    }
  }

  async function refreshDetail({ silent = true } = {}) {
    const targetCaseId = normalizeCaseId(caseId)
    if (!targetCaseId) {
      return null
    }

    try {
      const nextCaseDetail = await api.fetchCaseDetail(targetCaseId)
      caseDetail.value = nextCaseDetail
      statusForm.status = nextCaseDetail?.status || ''
      return nextCaseDetail
    } catch (error) {
      if (!silent) {
        notifier.error(extractFriendlyError(error, '案件详情刷新失败。'))
      }
      return null
    }
  }

  async function refreshFiles({ silent = true } = {}) {
    const targetCaseId = normalizeCaseId(caseId)
    if (!targetCaseId) {
      rawFiles.value = []
      return []
    }

    loadingFiles.value = true

    try {
      const nextFiles = await api.fetchCaseFiles(targetCaseId)
      rawFiles.value = Array.isArray(nextFiles) ? nextFiles : []
      return rawFiles.value
    } catch (error) {
      if (!silent) {
        notifier.error(extractFriendlyError(error, '案件文件列表加载失败。'))
      }
      return []
    } finally {
      loadingFiles.value = false
    }
  }

  async function updateStatus(nextStatus = statusForm.status) {
    const targetCaseId = normalizeCaseId(caseId)
    const previousStatus = caseDetail.value?.status || statusForm.status

    try {
      await api.updateCaseStatus(targetCaseId, nextStatus)
      notifier.success('案件状态已更新。')
      await Promise.all([refreshDetail(), refreshFiles()])
      return true
    } catch (error) {
      statusForm.status = previousStatus
      notifier.error(extractFriendlyError(error, '案件状态更新失败。'))
      return false
    }
  }

  async function uploadFile(file, options = {}) {
    const targetCaseId = normalizeCaseId(caseId)

    try {
      const uploaded = await api.uploadCaseFile(targetCaseId, file, options)
      notifier.success('文件上传成功，系统将自动重新分析。')
      await loadCase({ silent: true })
      return uploaded
    } catch (error) {
      notifier.error(extractFriendlyError(error, '文件上传失败。'))
      return null
    }
  }

  async function uploadRequest(options = {}) {
    const uploaded = await uploadFile(options.file, {
      description: options.data?.description || '',
      onProgress: options.onProgress,
    })

    if (!uploaded) {
      options.onError?.(new Error('upload failed'))
      return null
    }

    options.onSuccess?.(uploaded)
    return uploaded
  }

  async function downloadFile(file) {
    try {
      await api.downloadCaseFile(file)
      return true
    } catch (error) {
      notifier.error(extractFriendlyError(error, '文件下载失败。'))
      return false
    }
  }

  async function deleteFile(file) {
    try {
      await confirmDelete(`确认删除文件“${file?.file_name || '当前文件'}”吗？`, '删除文件', {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
      })
    } catch (error) {
      if (isCancelError(error)) {
        return false
      }
      notifier.error(extractFriendlyError(error, '删除文件失败。'))
      return false
    }

    try {
      await api.deleteCaseFile(file?.id)
      notifier.success('文件已删除。')
      rawFiles.value = rawFiles.value.filter((f) => f.id !== file?.id)
      return true
    } catch (error) {
      notifier.error(extractFriendlyError(error, '删除文件失败。'))
      return false
    }
  }

  async function loadInvitePath() {
    if (!caseCapabilities.value.actions.canGenerateInvite) {
      notifier.warning('当前用户无权生成邀请链接。')
      return ''
    }

    try {
      const nextInvitePath = await api.fetchCaseInvitePath(normalizeCaseId(caseId))
      invitePath.value = nextInvitePath
      return nextInvitePath
    } catch (error) {
      notifier.error(extractFriendlyError(error, '获取邀请链接失败。'))
      return ''
    }
  }

  async function copyInvitePath({
    clipboard = typeof navigator !== 'undefined' ? navigator.clipboard : null,
  } = {}) {
    if (!invitePath.value) {
      return false
    }

    try {
      if (typeof clipboard?.writeText !== 'function') {
        throw new Error('Clipboard API is unavailable.')
      }
      await clipboard.writeText(invitePath.value)
      notifier.success('邀请链接已复制到剪贴板。')
      return true
    } catch (error) {
      notifier.error(extractFriendlyError(error, '复制邀请链接失败。'))
      return false
    }
  }

  async function saveLawyerRemark(remark) {
    const targetCaseId = normalizeCaseId(caseId)
    if (!targetCaseId) return false

    try {
      await api.updateLawyerRemark(targetCaseId, remark)
      notifier.success('备注已保存。')
      await refreshDetail({ silent: true })
      return true
    } catch (error) {
      notifier.error(extractFriendlyError(error, '律师备注保存失败。'))
      return false
    }
  }

  return {
    caseDetail,
    caseStage,
    caseCapabilities,
    files,
    invitePath,
    loading,
    loadingFiles,
    statusForm,
    timelineItems,
    loadCase,
    refreshDetail,
    refreshFiles,
    updateStatus,
    uploadFile,
    uploadRequest,
    downloadFile,
    deleteFile,
    loadInvitePath,
    copyInvitePath,
    saveLawyerRemark,
  }
}
