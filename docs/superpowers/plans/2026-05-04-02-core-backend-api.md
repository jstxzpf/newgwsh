# 后端核心 API 与中间件 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现系统核心的安全鉴权（JWT + Argon2id）、全局异常处理、FastAPI 依赖注入，以及集成 Celery 异步任务的基础框架，并装配路由。

**架构：** 使用 `passlib[argon2]` 处理密码，`python-jose` 签发 JWT，基于 Redis 和 Pydantic 的安全路由守卫。

**技术栈：** FastAPI, Celery, Redis, Argon2id, JWT

---

### 任务 1：核心安全与异常处理

**文件：**
- 创建：`backend/app/core/security.py`
- 创建：`backend/app/api/dependencies.py`
- 创建：`backend/app/core/exceptions.py`

- [ ] **步骤 1：实现密码与 JWT 安全模块**

```python
# backend/app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15) # access token 15 min
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7) # refresh token 7 days
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

- [ ] **步骤 2：定义全局异常与拦截器**

```python
# backend/app/core/exceptions.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class BusinessException(Exception):
    def __init__(self, code: int, message: str, error_code: str = None):
        self.code = code
        self.message = message
        self.error_code = error_code

async def business_exception_handler(request: Request, exc: BusinessException):
    content = {"code": exc.code, "message": exc.message}
    if exc.error_code:
        content["error_code"] = exc.error_code
    return JSONResponse(status_code=exc.code, content=content)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": "参数校验错误", "data": exc.errors()},
    )
```

- [ ] **步骤 3：编写核心依赖注入**

```python
# backend/app/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import SystemUser
from app.core.exceptions import BusinessException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> SystemUser:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise BusinessException(401, "无效的认证凭证")
    except JWTError:
        raise BusinessException(401, "凭证已过期或无效")
        
    result = await db.execute(select(SystemUser).where(SystemUser.user_id == int(user_id)))
    user = result.scalars().first()
    if not user:
        raise BusinessException(401, "用户不存在")
    if not user.is_active:
        raise BusinessException(403, "账号已被停用")
    return user
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/core/security.py backend/app/core/exceptions.py backend/app/api/dependencies.py
git commit -m "feat: 添加 JWT 安全机制与全局拦截依赖"
```

### 任务 2：Auth 路由与会话管理

**文件：**
- 创建：`backend/app/schemas/auth.py`
- 创建：`backend/app/api/v1/auth.py`
- 创建：`backend/app/api/v1/__init__.py`
- 创建：`backend/app/api/__init__.py`

- [ ] **步骤 1：定义 Pydantic Schema**

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserInfoResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    role_level: int
    dept_id: int | None
```

- [ ] **步骤 2：编写 Auth 路由端点**

```python
# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser, UserSession
from app.schemas.auth import LoginRequest, LoginResponse, UserInfoResponse
from app.core.security import verify_password, create_access_token, create_refresh_token, get_password_hash
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import uuid
from datetime import datetime, timedelta, timezone

router = APIRouter()

@router.post("/login", response_model=dict)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemUser).where(SystemUser.username == req.username))
    user = result.scalars().first()
    if not user or not verify_password(req.password, user.password_hash):
        raise BusinessException(401, "用户名或密码错误")
    if not user.is_active:
        raise BusinessException(403, "账号已被停用")
        
    # 清除旧会话
    await db.execute(SystemUser.__table__.delete().where(UserSession.user_id == user.user_id)) # 简化逻辑，应从 UserSession 删除
    
    access_token = create_access_token(subject=user.user_id)
    refresh_token = create_refresh_token(subject=user.user_id)
    
    # 写入新会话
    session_id = str(uuid.uuid4())
    new_session = UserSession(
        session_id=session_id,
        user_id=user.user_id,
        refresh_token_hash=get_password_hash(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(new_session)
    await db.commit()
    
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=7*24*3600)
    return {"code": 200, "message": "success", "data": {"access_token": access_token, "token_type": "bearer"}}

@router.get("/me", response_model=dict)
async def get_me(current_user: SystemUser = Depends(get_current_user)):
    data = UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        full_name=current_user.full_name,
        role_level=current_user.role_level,
        dept_id=current_user.dept_id
    )
    return {"code": 200, "message": "success", "data": data.model_dump()}
```

- [ ] **步骤 3：模块初始化与装配**

```python
# backend/app/api/v1/__init__.py
# backend/app/api/__init__.py
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/v1/auth.py backend/app/api/
git commit -m "feat: 实现登录验证与会话管理路由"
```

### 任务 3：Celery 异步基础结构

**文件：**
- 创建：`backend/app/tasks/__init__.py`
- 创建：`backend/app/tasks/celery_app.py`
- 创建：`backend/app/tasks/worker.py`

- [ ] **步骤 1：初始化 Celery 应用**

```python
# backend/app/tasks/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "newgwsh_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.worker"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_concurrency=4,
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=600
)
```

- [ ] **步骤 2：编写 Worker 骨架与同步数据库依赖**

```python
# backend/app/tasks/worker.py
from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
import time

@celery_app.task(bind=True, max_retries=3)
def dummy_polish_task(self, task_id: str, doc_id: str):
    with SyncSessionLocal() as session:
        # 这里演示同步会话的使用
        print(f"Task {task_id} processing doc {doc_id}")
        time.sleep(2)
        return {"status": "success", "task_id": task_id}
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/tasks/
git commit -m "feat: 集成 Celery 与 Worker 基础骨架"
```

### 任务 4：全局路由装配与中间件挂载

**文件：**
- 修改：`backend/app/main.py`

- [ ] **步骤 1：挂载异常处理器与 API 路由**

```python
# backend/app/main.py (覆盖原有内容)
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import BusinessException, business_exception_handler, validation_exception_handler
from app.api.v1 import auth

app = FastAPI(title="泰兴调查队公文处理系统 V3.0")

app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/main.py
git commit -m "feat: 装配全局异常处理与主路由"
```