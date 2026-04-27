import ipaddress
import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings

class RoutingGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 如果没有配置白名单则放行
        if not settings.ALLOWED_SUBNETS:
            return await call_next(request)
            
        # 优先从 X-Forwarded-For 提取真实客户端 IP (支持 Nginx 等反向代理)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else None

        if not client_ip:

            return JSONResponse(status_code=403, content={"detail": "无法识别客户端 IP"})
            
        is_allowed = False
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            for subnet in settings.ALLOWED_SUBNETS:
                if ip_obj in ipaddress.ip_network(subnet, strict=False):
                    is_allowed = True
                    break
        except ValueError:
            pass # IP 解析错误
            
        if not is_allowed:
            return JSONResponse(status_code=403, content={"detail": "非法的子网来源，算力穿透被阻断。"})
            
        return await call_next(request)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 提取或生成 trace_id
        trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 绑定到当前协程上下文
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            client_ip=request.client.host if request.client else "unknown",
            method=request.method,
            path=request.url.path,
            user_id="anonymous" # 初始占位
        )
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        return response
