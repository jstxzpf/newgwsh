from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):
    APP_NAME: str = "NewGWSH"
    DEBUG: bool = False
    SECRET_KEY: str = "dev_secret_key_change_me_in_prod"
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "newgwsh"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    STORAGE_ROOT: str = "data/storage"

    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Lock Settings
    LOCK_TTL_DEFAULT: int = 180
    LOCK_HEARTBEAT_INTERVAL: int = 90

    # AI & Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:e4b"
    OLLAMA_EMBEDDING_MODEL: str = "bge-m3"
    OLLAMA_TIMEOUT_SECONDS: int = 120
    AI_RATE_LIMIT_PER_MINUTE: int = 5
    EMBEDDING_DIMENSION: int = 1024  # 适配 bge-m3

    # Lifecycle & Task Settings
    AUTO_SAVE_INTERVAL_SECONDS: int = 60
    TASK_MAX_RETRIES: int = 3
    GIN_CLEANUP_BATCH_SIZE: int = 5000
    
    # Security & SIP
    SIP_SECRET_KEY: str = "sip_secret_key_change_me_in_prod"

    # Infrastructure Paths
    ARCHIVE_ROOT: str = "data/archive"
    PROMPTS_ROOT: str = "app/prompts"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    REDIS_URL: str = "redis://localhost:6379/1"

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
