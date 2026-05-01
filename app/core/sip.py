import unicodedata
import re
import hmac
import hashlib
from app.core.config import settings

def normalize_for_sip(text: str) -> str:
    """
    国家统计局泰兴调查队公文归一化流水线 (符合设计方案 3.3)
    """
    if not text:
        return ""
        
    # 1. NFKC 兼容性等价分解
    text = unicodedata.normalize('NFKC', text)
    
    # 2. 换行符归一化 (\r\n -> \n)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 3. 对存证分隔符进行转义
    text = text.replace('|', '\\|')
    
    # 4. 压缩连续的非换行空白符为单个空格
    text = re.sub(r'[^\S\n]+', ' ', text)
    
    # 5. 压缩连续换行为单换行
    text = re.sub(r'\n+', '\n', text)
    
    # 6. 首尾去除
    text = text.strip()
    return text

def generate_sip_hash(content: str, reviewer_id: int, reviewed_at_iso: str) -> str:
    """
    基于 HMAC-SHA256 的 SIP 指纹生成
    公式: normalized_content | reviewer_user_id | reviewed_at_iso8601
    """
    normalized = normalize_for_sip(content)
    if not normalized:
        return ""
        
    raw_payload = f"{normalized}|{reviewer_id}|{reviewed_at_iso}"
    
    # 使用 SECRET_KEY 作为签名密钥
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        raw_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature
