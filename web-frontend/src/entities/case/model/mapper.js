import { buildCaseFileCapabilities } from './policy'

function normalizeList(items) {
  return Array.isArray(items) ? items : []
}

export function mapCaseTimelineItems(items = []) {
  return normalizeList(items).map((item, index) => ({
    ...item,
    timelineKey: `${item?.event_type || 'event'}-${item?.occurred_at || 'unknown'}-${index}`,
  }))
}

export function mapCaseFileItems(items = [], { viewer = null, caseItem = null, caseCapabilities = null } = {}) {
  return normalizeList(items).map((item) => ({
    ...item,
    capabilities: buildCaseFileCapabilities({
      viewer,
      caseItem,
      fileItem: item,
      caseCapabilities,
    }),
  }))
}
