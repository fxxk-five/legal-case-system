import { clearSession, getAccessToken, getUserInfo } from "./auth";

export function requireLogin() {
  if (getAccessToken()) {
    return true;
  }
  uni.reLaunch({ url: "/pages/login/index" });
  return false;
}

export function getCurrentUser() {
  return getUserInfo();
}

export function redirectByRole(user = getCurrentUser()) {
  if (!user) {
    uni.reLaunch({ url: "/pages/login/index" });
    return;
  }
  if (user.role === "client") {
    uni.reLaunch({ url: "/pages/client/case-detail" });
    return;
  }
  uni.reLaunch({ url: "/pages/lawyer/home" });
}

export function logoutAndRedirect() {
  clearSession();
  uni.reLaunch({ url: "/pages/login/index" });
}
