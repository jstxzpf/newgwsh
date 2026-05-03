from pydantic import BaseModel
from typing import Optional
from app.models.enums import KBTier, DataSecurityLevel

class KBUploadRequest(BaseModel):
    parent_id: Optional[int] = None
    kb_tier: KBTier = KBTier.PERSONAL
    security_level: DataSecurityLevel = DataSecurityLevel.GENERAL
    # 注意：实际文件上传需要使用 Form 和 UploadFile，这里仅定义依赖参数。