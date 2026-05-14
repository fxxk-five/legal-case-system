import { showFormError } from "../../shared/lib/form";
import { getCurrentUser, redirectByRole, requireLogin } from "../auth/session";
import { buildClientMenuState, buildWorkspaceMenuState, getWorkspaceAccessResult } from "../auth/role-routing";

export function buildWorkspaceMenu(user, currentKey = "") {
  return buildWorkspaceMenuState(user, currentKey);
}

export function buildClientMenu(currentKey = "") {
  return buildClientMenuState(currentKey);
}

export function ensureWorkspaceAccess(options = {}) {
  if (!requireLogin()) {
    return null;
  }

  const user = getCurrentUser();
  const access = getWorkspaceAccessResult(user, options);
  if (!access.ok) {
    showFormError(access.message);
    redirectByRole(user);
    return null;
  }

  return user;
}

export function openWorkspacePage(path) {
  if (!path) {
    return;
  }

  uni.reLaunch({ url: path });
}
