import enum

class DocumentStatus(str, enum.Enum):
    DRAFTING = "DRAFTING"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class KBTier(str, enum.Enum):
    BASE = "BASE"
    DEPT = "DEPT"
    PERSONAL = "PERSONAL"

class DataSecurityLevel(str, enum.Enum):
    CORE = "CORE"
    IMPORTANT = "IMPORTANT"
    GENERAL = "GENERAL"

class DocTypeEnum(str, enum.Enum):
    NOTICE = "NOTICE"
    REQUEST = "REQUEST"
    REPORT = "REPORT"
    REPLY = "REPLY"
    LETTER = "LETTER"
    MINUTES = "MINUTES"
    RESEARCH = "RESEARCH"
    ECONOMIC_INFO = "ECONOMIC_INFO"
    GENERAL = "GENERAL"

class TaskType(str, enum.Enum):
    POLISH = "POLISH"
    FORMAT = "FORMAT"
    PARSE = "PARSE"

class TaskStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"