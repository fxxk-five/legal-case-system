const ENV_ALIASES = {
  local: "local",
  dev: "local",
  development: "local",
  test: "staging",
  testing: "staging",
  stage: "staging",
  staging: "staging",
  prod: "production",
  production: "production",
};

const ENV_CONFIGS = {
  local: {
    apiBaseUrl: "http://127.0.0.1:8000/api/v1",
  },
  staging: {
    apiBaseUrl: "https://staging.your-domain.example/api/v1",
  },
  production: {
    apiBaseUrl: "https://your-domain.example/api/v1",
  },
};

function readProcessEnv(name) {
  if (typeof process === "undefined" || !process?.env) {
    return "";
  }

  const value = process.env[name];
  return typeof value === "string" ? value.trim() : "";
}

function normalizeEnvName(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return ENV_ALIASES[normalized] || "local";
}

function resolveAppEnv() {
  return normalizeEnvName(
    readProcessEnv("UNI_APP_RUNTIME_ENV") ||
      readProcessEnv("VUE_APP_RUNTIME_ENV") ||
      readProcessEnv("APP_ENV") ||
      readProcessEnv("NODE_ENV"),
  );
}

function resolveApiBaseUrl(appEnv) {
  return (
    readProcessEnv("UNI_APP_API_BASE_URL") ||
    readProcessEnv("VUE_APP_API_BASE_URL") ||
    readProcessEnv("API_BASE_URL") ||
    ENV_CONFIGS[appEnv]?.apiBaseUrl ||
    ENV_CONFIGS.local.apiBaseUrl
  );
}

const appEnv = resolveAppEnv();

export const config = {
  appEnv,
  apiBaseUrl: resolveApiBaseUrl(appEnv),
};
