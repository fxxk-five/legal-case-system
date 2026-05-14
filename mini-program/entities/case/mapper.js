import { formatDateTime } from "../../shared/lib/display";
import { buildCaseFileCapabilities } from "./policy";

function normalizeList(items) {
  return Array.isArray(items) ? items : [];
}

export function formatCaseFileParseStatusText(value) {
  const map = {
    pending: "待解析",
    processing: "解析中",
    completed: "已解析",
    failed: "解析失败",
  };
  return map[String(value || "").toLowerCase()] || value || "待解析";
}

export function mapCaseTimelineItems(items = [], { actorResolver = null } = {}) {
  return normalizeList(items).map((item, index) => ({
    ...item,
    timeline_key: `${item?.event_type || "event"}-${item?.occurred_at || "unknown"}-${index}`,
    occurred_at_text: formatDateTime(item?.occurred_at, "-"),
    actor_text: typeof actorResolver === "function" ? actorResolver(item) : String(item?.operator_name || "系统"),
    description_text: item?.description || item?.title || "-",
  }));
}

export function mapCaseFileItems(
  items = [],
  {
    viewer = null,
    caseItem = null,
    caseCapabilities = null,
    parseStatusText = formatCaseFileParseStatusText,
  } = {},
) {
  return normalizeList(items).map((item) => ({
    ...item,
    parse_status_text: parseStatusText(item?.parse_status),
    created_at_text: formatDateTime(item?.created_at, "-"),
    capabilities: buildCaseFileCapabilities({
      viewer,
      caseItem,
      fileItem: item,
      caseCapabilities,
    }),
  }));
}

export function collectMissingEvidenceHints(latestAnalysis = null) {
  if (!latestAnalysis) {
    return [];
  }

  const weaknesses = Array.isArray(latestAnalysis.weaknesses) ? latestAnalysis.weaknesses : [];
  const recommendations = Array.isArray(latestAnalysis.recommendations) ? latestAnalysis.recommendations : [];

  return [...new Set([...weaknesses, ...recommendations].map((item) => String(item || "").trim()).filter(Boolean))].slice(0, 5);
}
