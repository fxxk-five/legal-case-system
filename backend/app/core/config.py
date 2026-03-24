from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    PROJECT_NAME: str = "Legal Case System"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "legal_case"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 13
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    WECHAT_MINIAPP_APP_ID: str = ""
    WECHAT_MINIAPP_APP_SECRET: str = ""
    WECHAT_MINIAPP_MOCK_LOGIN: bool = True
    WECHAT_MINIAPP_CLIENT_ENTRY_PAGE: str = "pages/login/index"
    FILE_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    FILE_UPLOAD_MAX_SIZE_BYTES: int = 50 * 1024 * 1024
    FILE_UPLOAD_ALLOWED_EXTENSIONS: list[str] = [
        ".pdf",
        ".doc",
        ".docx",
        ".jpg",
        ".jpeg",
        ".png",
        ".xls",
        ".xlsx",
        ".txt",
    ]
    FILE_UPLOAD_ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "text/plain",
    ]

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    LOCAL_STORAGE_DIR: str = "storage"
    STORAGE_BACKEND: str = "local"
    STORAGE_DIRECT_UPLOAD_ENABLED: bool = False
    STORAGE_DELETE_POLICY: str = "immediate"
    STORAGE_RETENTION_PREFIX: str = "_retained"
    STORAGE_PENDING_PREFIX: str = "_pending"
    STORAGE_PUBLIC_BASE_URL: str = ""
    TENCENT_COS_SECRET_ID: str = ""
    TENCENT_COS_SECRET_KEY: str = ""
    TENCENT_COS_BUCKET: str = ""
    TENCENT_COS_REGION: str = ""
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_REGION: str = ""

    # AI settings
    AI_ENABLED: bool = True
    AI_MOCK_MODE: bool = True
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = "gpt-5.4"
    AI_MODEL: str = ""
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_TIMEOUT_SECONDS: int = 60
    AI_TOKEN_COST_PER_1K: float = 0.03
    AI_DAILY_TOKEN_LIMIT: int = 100000
    QUEUE_DRIVER: str = "db"
    AI_DB_QUEUE_EAGER: bool = False
    AI_DB_QUEUE_EAGER_BLOCKING: bool = False
    AI_DB_QUEUE_POLL_SECONDS: float = 2.0
    AI_DB_QUEUE_MAX_RETRIES: int = 3
    AI_DB_QUEUE_RETRY_BACKOFF_SECONDS: int = 30
    AI_DB_QUEUE_STALE_TASK_SECONDS: int = 900
    AI_DB_QUEUE_HEARTBEAT_FILE: str = "/tmp/legal-ai-worker-heartbeat.json"
    AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS: int = 90
    AI_DB_QUEUE_WORKER_ID: str = ""
    TENCENT_QUEUE_REGION: str = ""
    TENCENT_QUEUE_NAMESPACE: str = ""
    TENCENT_QUEUE_TOPIC_NAME: str = ""
    TENCENT_QUEUE_SUBSCRIPTION_NAME: str = ""
    TENCENT_QUEUE_ENDPOINT: str = ""
    TENCENT_QUEUE_SECRET_ID: str = ""
    TENCENT_QUEUE_SECRET_KEY: str = ""
    AI_MONTHLY_BUDGET_LIMIT: float | None = None
    AI_CASE_BUDGET_LIMIT: float | None = None
    AI_BUDGET_DEGRADE_MODEL: str = ""
    REPORT_SERVICE_BASE_URL: str = ""
    REPORT_SERVICE_TIMEOUT_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("AI_MONTHLY_BUDGET_LIMIT", "AI_CASE_BUDGET_LIMIT", mode="before")
    @classmethod
    def _empty_budget_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def EFFECTIVE_OPENAI_BASE_URL(self) -> str:
        return (self.OPENAI_BASE_URL or self.OPENAI_API_BASE).strip()

    @computed_field
    @property
    def EFFECTIVE_AI_MODEL(self) -> str:
        return (self.AI_MODEL or self.OPENAI_MODEL).strip()

    @computed_field
    @property
    def IS_PRODUCTION(self) -> bool:
        return (self.APP_ENV or "").strip().lower() in {"prod", "production", "staging"}

    @model_validator(mode="after")
    def validate_ai_runtime_config(self) -> "Settings":
        if self.IS_PRODUCTION and self.SECRET_KEY == "change-me-in-production":
            raise ValueError("SECRET_KEY must be overridden outside development and test environments")
        if self.IS_PRODUCTION and any("localhost" in origin or "127.0.0.1" in origin for origin in self.BACKEND_CORS_ORIGINS):
            raise ValueError("BACKEND_CORS_ORIGINS must not include localhost origins outside development and test environments")
        if self.IS_PRODUCTION and self.AI_ENABLED and self.AI_MOCK_MODE:
            raise ValueError("AI_MOCK_MODE must be disabled outside development and test environments")
        if not self.AI_ENABLED or self.AI_MOCK_MODE:
            return self
        if not self.OPENAI_API_KEY.strip():
            raise ValueError("OPENAI_API_KEY must be set when AI mock mode is disabled")
        if not self.EFFECTIVE_OPENAI_BASE_URL:
            raise ValueError("OPENAI_BASE_URL or OPENAI_API_BASE must be set when AI mock mode is disabled")
        if not self.EFFECTIVE_AI_MODEL:
            raise ValueError("AI_MODEL or OPENAI_MODEL must be set when AI mock mode is disabled")
        return self


settings = Settings()
