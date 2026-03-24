const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_INFO_KEY = "user_info";
const OPENID_KEY = "wechat_openid";

export function getAccessToken() {
  return uni.getStorageSync(ACCESS_TOKEN_KEY) || "";
}

export function setAccessToken(token) {
  uni.setStorageSync(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken() {
  uni.removeStorageSync(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return uni.getStorageSync(REFRESH_TOKEN_KEY) || "";
}

export function setRefreshToken(token) {
  if (!token) {
    uni.removeStorageSync(REFRESH_TOKEN_KEY);
    return;
  }
  uni.setStorageSync(REFRESH_TOKEN_KEY, token);
}

export function clearRefreshToken() {
  uni.removeStorageSync(REFRESH_TOKEN_KEY);
}

export function getUserInfo() {
  return uni.getStorageSync(USER_INFO_KEY) || null;
}

export function setUserInfo(user) {
  uni.setStorageSync(USER_INFO_KEY, user);
}

export function clearUserInfo() {
  uni.removeStorageSync(USER_INFO_KEY);
}

export function getWechatOpenid() {
  return uni.getStorageSync(OPENID_KEY) || "";
}

export function setWechatOpenid(openid) {
  uni.setStorageSync(OPENID_KEY, openid);
}

export function clearWechatOpenid() {
  uni.removeStorageSync(OPENID_KEY);
}

export function clearSession() {
  clearAccessToken();
  clearRefreshToken();
  clearUserInfo();
  clearWechatOpenid();
}
