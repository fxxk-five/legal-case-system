import { clearSession, getAccessToken, getUserInfo, setUserInfo } from "./auth";
import { showFormError } from "../../shared/lib/form";
import { get, logoutByServer } from "../../shared/api/http";
import { getClientAccessResult, LOGIN_PAGE, resolveUserHomeUrl } from "./role-routing";

function shouldClearSessionBeforeRedirect(url) {
  return typeof url === "string" && url.startsWith(LOGIN_PAGE);
}

export function requireLogin() {
  // 检查是否有有效的访问令牌，无则重定向到登录页
  if (getAccessToken()) {
    return true;
  }
  uni.reLaunch({ url: LOGIN_PAGE });
  return false;
}

export function getCurrentUser() {
  return getUserInfo();
}

export function ensureClientAccess() {
  if (!requireLogin()) {
    return null;
  }

  const user = getCurrentUser();
  const access = getClientAccessResult(user);
  if (!access.ok) {
    showFormError(access.message);
    redirectByRole(user);
    return null;
  }

  return user;
}

export async function redirectByRole(user = getCurrentUser()) {
  if (!user) {
    uni.reLaunch({ url: LOGIN_PAGE });
    return;
  }

  if (user.role === "client") {
    let cases = [];
    try {
      const result = await get("/cases");
      cases = Array.isArray(result) ? result : [];
    } catch {
      cases = [];
    }
    const nextUrl = resolveUserHomeUrl(user, cases);
    if (shouldClearSessionBeforeRedirect(nextUrl)) {
      clearSession();
    }
    uni.reLaunch({ url: nextUrl });
    return;
  }

  let nextUser = user;
  try {
    const profile = await get("/users/me");
    nextUser = {
      ...user,
      ...(profile || {}),
    };
    try {
      const tenant = await get("/tenants/current");
      if (tenant?.type) {
        nextUser = {
          ...nextUser,
          tenant_type: tenant.type,
        };
      }
    } catch {
      nextUser = {
        ...nextUser,
        tenant_type: nextUser?.tenant_type || user?.tenant_type || "",
      };
    }
    setUserInfo(nextUser);
  } catch {
    nextUser = user;
  }

  const nextUrl = resolveUserHomeUrl(nextUser);
  if (shouldClearSessionBeforeRedirect(nextUrl)) {
    clearSession();
  }
  uni.reLaunch({ url: nextUrl });
}

export async function logoutAndRedirect() {
  // 完整登出流程：通知后端 + 清除本地会话 + 重定向到登录页
  await logoutByServer();
  clearSession();
  uni.reLaunch({ url: LOGIN_PAGE });
}
