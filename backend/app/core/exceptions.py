class TaixingException(Exception):
    """泰兴系统基础异常类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DocumentLockedError(TaixingException):
    """公文被他人锁定"""
    pass

class DocumentPermissionError(TaixingException):
    """公文权限不足"""
    pass

class DocumentStateError(TaixingException):
    """公文状态不正确"""
    pass
