import hashlib
import os

def calculate_hash(file_content: bytes) -> str:
    """计算 SHA-256 哈希值"""
    return hashlib.sha256(file_content).hexdigest()

def get_storage_path(content_hash: str, filename: str) -> str:
    """
    根据哈希值生成分级存储路径
    示例: ab/cd/abcdef123456_filename.ext
    """
    p1 = content_hash[:2]
    p2 = content_hash[2:4]
    return os.path.join(p1, p2, f"{content_hash}_{filename}")
