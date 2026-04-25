from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "泰兴市国家统计局公文处理系统"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "taixing_nbs"
    
    # 获取异步与同步连接字符串
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def SYNC_DATABASE_URI(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 安全与鉴权
    SECRET_KEY: str = "change_this_to_a_secure_random_string"
    SIP_SECRET_KEY: str = "sip_secure_random_string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ALLOWED_SUBNETS: List[str] = ["10.132.0.0/16", "127.0.0.1"]
    
    # 业务参数
    LOCK_TTL_SECONDS: int = 180
    HEARTBEAT_INTERVAL_SECONDS: int = 90
    RETRY_BACKOFF_BASE_SECONDS: int = 2
    RETRY_BACKOFF_MAX_SECONDS: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
