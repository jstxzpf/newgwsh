from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router
from app.api.middleware import RoutingGuardMiddleware, RequestIDMiddleware
from app.core.logger import setup_logging
from fastapi.middleware.trustedhost import TrustedHostMiddleware

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RoutingGuardMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "ok"}
