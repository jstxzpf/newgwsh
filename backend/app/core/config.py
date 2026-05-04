from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "泰兴调查队公文处理系统"
    VERSION: str = "3.0"
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    
    REDIS_URL: str
    OLLAMA_BASE_URL: str
    SECRET_KEY: str
    SIP_SECRET_KEY: str
    
    # 系统运行参数 (对齐 §四)
    LOCK_TTL: int = 180
    HEARTBEAT_INTERVAL: int = 90
    AUTO_SAVE_INTERVAL: int = 60
    MAX_SSE_CONNECTIONS: int = 5
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def sync_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()