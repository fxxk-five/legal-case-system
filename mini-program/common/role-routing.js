import { getUserInfo } from "./auth";
import {
  isAccessRestrictedRole,
  isTenantAdmin,
  isUserApproved,
  isWorkspaceRole,
} from "./display";

export const LOGIN_PAGE = "/pages/login/index";
export const LOGIN_STATUS_PENDING_APPROVAL = "pending-approval";
export const LOGIN_STATUS_ACCESS_RESTRICTED = "access-restricted";
export const ORG_WORKSPACE_HOME_PAGE = "/pages/lawyer/home";
export const SOLO_WORKSPACE_HOME_PAGE = "/pages/lawyer/cases";
export const CLIENT_CASE_LIST_PAGE = "/pages/client/case-list";
export const MY_PAGE = "/pages/common/my";

const WORKSPACE_MENU_REGISTRY = {
  overview: { key: "overview", label: "\u6982\u89c8", path: "/pages/lawyer/home" },
  cases: { key: "cases", label: "\u6848\u4ef6", path: "/pages/lawyer/cases" },
  clients: { key: "clients", label: "\u5f53\u4e8b\u4eba", path: "/pages/lawyer/clients" },
  lawyers: { key: "lawyers", label: "\u5f8b\u5e08", path: "/pages/lawyer/lawyers" },
  my: { key: "my", label: "\u6211\u7684", path: MY_PAGE },
};

const TENANT_ADMIN_MENU_KEYS = ["overview", "cases", "clients", "lawyers", "my"];
const ORG_LAWYER_MENU_KEYS = ["overview", "cases", "clients", "my"];
const PERSONAL_LAWYER_MENU_KEYS = ["cases", "my"];

const CLIENT_MENU_ITEMS = [
  { key: "cases", label: "\u6848\u4ef6", path: CLIENT_CASE_LIST_PAGE },
  { key: "my", label: "\u6211\u7684", path: MY_PAGE },
];

function buildPageUrl(path, query = {}) {
  const search = Object.keys(query)
    .filter((key) => query[key] !== undefined && query[key] !== null && query[key] !== "")
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(String(query[key]))}`)
    .join("&");
  return search ? `${path}?${search}` : path;
}

function getLoginStatusForUser(user) {
  if (!user) {
    return "";
  }
  if (!isUserApproved(user)) {
    return LOGIN_STATUS_PENDING_APPROVAL;
  }
  if (isAccessRestrictedRole(user)) {
    return LOGIN_STATUS_ACCESS_RESTRICTED;
  }
  return "";
}

export function buildLoginPageUrl(token = "", scene = "", loginStatus = "") {
  return buildPageUrl(LOGIN_PAGE, {
    token: token || undefined,
    scene: scene || undefined,
    status: loginStatus || undefined,
  });
}

export function getWorkspaceMenuItems(user = getUserInfo()) {
  const tenantType = String(user?.tenant_type || "");
  const menuKeys = tenantType === "personal"
    ? PERSONAL_LAWYER_MENU_KEYS
    : (isTenantAdmin(user) ? TENANT_ADMIN_MENU_KEYS : ORG_LAWYER_MENU_KEYS);

  return menuKeys
    .map((key) => WORKSPACE_MENU_REGISTRY[key])
    .filter(Boolean);
}

export function buildWorkspaceMenuState(user, currentKey = "") {
  return getWorkspaceMenuItems(user).map((item) => ({
    ...item,
    current: item.key === currentKey,
    class_name: item.key === currentKey ? "workspace-menu-item-active" : "",
  }));
}

export function getClientMenuItems() {
  return CLIENT_MENU_ITEMS;
}

export function buildClientMenuState(currentKey = "") {
  return getClientMenuItems().map((item) => ({
    ...item,
    current: item.key === currentKey,
    class_name: item.key === currentKey ? "workspace-menu-item-active" : "",
  }));
}

export function getWorkspaceHomeUrl(user = getUserInfo()) {
  if (String(user?.tenant_type || "") === "personal") {
    return SOLO_WORKSPACE_HOME_PAGE;
  }
  const items = getWorkspaceMenuItems(user);
  return items.length ? items[0].path : ORG_WORKSPACE_HOME_PAGE;
}

export function getWorkspaceModuleUrl(key, user = getUserInfo()) {
  const items = getWorkspaceMenuItems(user);
  const target = items.find((item) => item.key === key);
  return target ? target.path : getWorkspaceHomeUrl(user);
}

export function buildClientCaseDetailUrl(caseId) {
  return buildPageUrl("/pages/client/case-detail", { id: caseId });
}

export function buildMyPageUrl(query = {}) {
  return buildPageUrl(MY_PAGE, query);
}

export function buildCreateCaseUrl() {
  return "/pages/lawyer/create-case";
}

export function buildWorkspaceCaseDetailUrl(caseId, query = {}) {
  return buildPageUrl("/pages/lawyer/case-detail", {
    id: caseId,
    ...query,
  });
}

export function buildWorkspaceClientDetailUrl(clientId) {
  return buildPageUrl("/pages/lawyer/clients", { id: clientId });
}

export function buildWorkspaceLawyerDetailUrl(lawyerId, scope = "") {
  return buildPageUrl("/pages/lawyer/lawyers", { id: lawyerId, scope });
}

export function getClientHomeUrl(cases = []) {
  if (Array.isArray(cases) && cases.length === 1 && cases[0] && cases[0].id) {
    return buildClientCaseDetailUrl(cases[0].id);
  }
  return CLIENT_CASE_LIST_PAGE;
}

export function resolveUserHomeUrl(user, cases = []) {
  if (!user) {
    return LOGIN_PAGE;
  }

  const loginStatus = getLoginStatusForUser(user);
  if (loginStatus) {
    return buildLoginPageUrl("", "", loginStatus);
  }

  if (user.role === "client") {
    return getClientHomeUrl(cases);
  }

  if (isWorkspaceRole(user)) {
    return getWorkspaceHomeUrl(user);
  }

  return buildLoginPageUrl("", "", LOGIN_STATUS_ACCESS_RESTRICTED);
}

export function getWorkspaceAccessResult(user, options = {}) {
  if (!user) {
    return {
      ok: false,
      message: "\u8bf7\u5148\u767b\u5f55\u3002",
    };
  }

  if (!isUserApproved(user)) {
    return {
      ok: false,
      message: "\u5f53\u524d\u8d26\u53f7\u6b63\u5728\u7b49\u5f85\u5ba1\u6279\u3002",
    };
  }

  if (isAccessRestrictedRole(user) || !isWorkspaceRole(user)) {
    return {
      ok: false,
      message: "\u5f53\u524d\u89d2\u8272\u65e0\u6cd5\u8bbf\u95ee\u5de5\u4f5c\u53f0\u3002",
    };
  }

  if (options.adminOnly && !isTenantAdmin(user)) {
    return {
      ok: false,
      message: "\u5f53\u524d\u8d26\u53f7\u65e0\u6cd5\u8bbf\u95ee\u8be5\u9875\u9762\u3002",
    };
  }

  return { ok: true };
}

export function getClientAccessResult(user) {
  if (!user) {
    return {
      ok: false,
      message: "\u8bf7\u5148\u767b\u5f55\u3002",
    };
  }

  if (!isUserApproved(user)) {
    return {
      ok: false,
      message: "\u5f53\u524d\u8d26\u53f7\u6b63\u5728\u7b49\u5f85\u5ba1\u6279\u3002",
    };
  }

  if (user.role !== "client") {
    return {
      ok: false,
      message: "\u5f53\u524d\u8d26\u53f7\u65e0\u6cd5\u8bbf\u95ee\u5f53\u4e8b\u4eba\u5de5\u4f5c\u53f0\u3002",
    };
  }

  return { ok: true };
}
