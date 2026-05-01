from datetime import datetime, timedelta, timezone
from typing import Any, Union
import jwt
import uuid
from argon2 import PasswordHasher
from app.core.config import settings

ph = PasswordHasher()

def get_password_hash(password: str) -> str:
    """使用 Argon2id 算法加密密码"""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码"""
    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """创建 Access Token (包含 JTI 用于单设备登录)"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    jti = str(uuid.uuid4())
    to_encode = {"exp": expire, "sub": str(subject), "type": "access", "jti": jti}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """创建 Refresh Token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    jti = str(uuid.uuid4())
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh", "jti": jti}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """解码 Token"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
