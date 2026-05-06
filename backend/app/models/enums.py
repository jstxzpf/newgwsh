import enum

class DocumentStatus(str, enum.Enum):
    DRAFTING = "DRAFTING"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"

class KBTier(str, enum.Enum):
    BASE = "BASE"
    DEPT = "DEPT"
    PERSONAL = "PERSONAL"

class DataSecurityLevel(str, enum.Enum):
    CORE = "CORE"
    IMPORTANT = "IMPORTANT"
    GENERAL = "GENERAL"

class KBTypeEnum(str, enum.Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"

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

class WorkflowNodeId(int, enum.Enum):
    DRAFTING = 10
    SNAPSHOT = 11
    SNAPSHOT_RESTORE = 12
    POLISH_REQUESTED = 20
    POLISH_APPLIED = 21
    FORMAT_REQUESTED = 22
    FORMAT_COMPLETED = 23
    SUBMITTED = 30
    REVIEWED = 31
    APPROVED = 40
    REJECTED = 41
    REVISION = 42
    ISSUED = 43
    ARCHIVED = 50

class NotificationType(str, enum.Enum):
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    DOC_APPROVED = "DOC_APPROVED"
    DOC_REJECTED = "DOC_REJECTED"
    LOCK_RECLAIMED = "LOCK_RECLAIMED"