import re
import unicodedata
import hmac
import hashlib
from datetime import datetime
from app.core.config import settings

class SIPService:
    @staticmethod
    def normalize_for_sip(text: str) -> str:
        if not text:
            return ""
            
        # 1. NFKC 归一化全角半角等字符
        text = unicodedata.normalize('NFKC', text)
        
        # 2. 换行符统一
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 3. 转义存证分割符
        text = text.replace('|', '\\|')
        
        # 4. 压缩空白（非换行）
        text = re.sub(r'[^\S\n]+', ' ', text)
        text = re.sub(r' +', ' ', text)
        
        # 5. 去除首尾空白
        return text.strip()

    @staticmethod
    def generate_sip_fingerprint(content: str, reviewer_id: int, reviewed_at: datetime) -> str | None:
        normalized_content = SIPService.normalize_for_sip(content)
        
        if not normalized_content:
            return None # 拒绝为无意义空文生成防伪签章
            
        # 修正：移除微秒并使用标准 ISO 格式，防止数据库精度不匹配导致校验失败
        iso_time = reviewed_at.replace(microsecond=0).isoformat()
        
        # 拼接原串公式
        raw_string = f"{normalized_content}|{reviewer_id}|{iso_time}"
        
        # 使用 HMAC-SHA256
        mac = hmac.new(
            settings.SIP_SECRET_KEY.encode('utf-8'),
            msg=raw_string.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return mac.hexdigest()
