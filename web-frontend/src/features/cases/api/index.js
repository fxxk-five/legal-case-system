import http from '../../../shared/api/http'
import { casesApi, filesApi, remarksApi } from './domain-api'

export { aiTasksApi, casesApi, filesApi, remarksApi } from './domain-api'

function getBrowserOrigin() {
  if (typeof window === 'undefined' || !window.location?.origin) {
    return ''
  }
  return window.location.origin
}

function triggerBrowserDownload({ href, fileName, target = '', doc = typeof document !== 'undefined' ? document : null }) {
  if (!doc?.body || typeof doc.createElement !== 'function') {
    throw new Error('Browser download is unavailable in the current environment.')
  }

  const link = doc.createElement('a')
  link.href = href
  if (fileName) {
    link.setAttribute('download', fileName)
  }
  if (target) {
    link.setAttribute('target', target)
  }
  link.setAttribute('rel', 'noopener')
  doc.body.appendChild(link)
  link.click()
  link.remove()
}

export async function fetchCaseDetail(caseId, { httpClient = http } = {}) {
  return casesApi.getCaseDetail(caseId, { httpClient })
}

export async function fetchCaseFiles(caseId, { httpClient = http } = {}) {
  return filesApi.listCaseFiles(caseId, { httpClient })
}

export async function fetchCaseDetailBundle(caseId, dependencies = {}) {
  const [caseDetail, files] = await Promise.all([
    fetchCaseDetail(caseId, dependencies),
    fetchCaseFiles(caseId, dependencies),
  ])

  return {
    caseDetail,
    files,
  }
}

export async function updateCaseStatus(caseId, status, { httpClient = http } = {}) {
  return casesApi.updateCaseStatus(caseId, status, { httpClient })
}

export async function uploadCaseFile(caseId, file, options = {}, dependencies = {}) {
  return filesApi.uploadCaseFile(caseId, file, options, dependencies)
}

export async function fetchCaseInvitePath(
  caseId,
  {
    httpClient = http,
    origin = getBrowserOrigin(),
  } = {},
) {
  const data = await casesApi.getCaseInviteQrcode(caseId, { httpClient })
  const directPath = String(data?.path || '').trim()
  if (directPath) {
    return directPath
  }

  const token = String(data?.token || '').trim()
  return token && origin ? `${origin}/invite/${token}` : ''
}

export async function fetchCaseFileAccessUrl(fileId, { httpClient = http } = {}) {
  const data = await filesApi.getFileAccessLink(fileId, { httpClient })
  const accessUrl = String(data?.access_url || '').trim()

  if (!accessUrl) {
    throw new Error('missing access url')
  }

  return accessUrl
}

export async function downloadCaseFile(
  fileItem,
  {
    httpClient = http,
    doc = typeof document !== 'undefined' ? document : null,
    urlApi = typeof URL !== 'undefined' ? URL : null,
  } = {},
) {
  const accessUrl = await fetchCaseFileAccessUrl(fileItem?.id, { httpClient })

  if (accessUrl.startsWith('http')) {
    triggerBrowserDownload({
      href: accessUrl,
      fileName: fileItem?.file_name || '',
      target: '_blank',
      doc,
    })
    return accessUrl
  }

  if (!urlApi?.createObjectURL || !urlApi?.revokeObjectURL) {
    throw new Error('Blob download is unavailable in the current environment.')
  }

  const response = await httpClient.get(accessUrl, { responseType: 'blob' })
  const blobUrl = urlApi.createObjectURL(response.data)

  try {
    triggerBrowserDownload({
      href: blobUrl,
      fileName: fileItem?.file_name || '',
      doc,
    })
    return accessUrl
  } finally {
    urlApi.revokeObjectURL(blobUrl)
  }
}

export async function deleteCaseFile(fileId, { httpClient = http } = {}) {
  return filesApi.deleteFile(fileId, { httpClient })
}

export async function updateLawyerRemark(caseId, remark, { httpClient = http } = {}) {
  return remarksApi.updateLawyerRemark(caseId, remark, { httpClient })
}

