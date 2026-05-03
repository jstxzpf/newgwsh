import unicodedata
import re
import hmac
import hashlib
from app.core.config import settings

def normalize_for_sip(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('|', '\\|')
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def generate_sip_hash(content: str, reviewer_id: int, reviewed_at_iso: str) -> str:
    normalized = normalize_for_sip(content)
    raw_str = f"{normalized}|{reviewer_id}|{reviewed_at_iso}"
    return hmac.new(settings.SIP_SECRET_KEY.encode(), raw_str.encode(), hashlib.sha256).hexdigest()