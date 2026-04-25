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

class WorkflowNode(int, enum.Enum):
    DRAFTING = 10
    POLISH = 12
    FINAL_LAYOUT = 22
    SUBMITTED = 30
    APPROVED = 40
    REJECTED = 41
    REVISION = 42

class TaskType(str, enum.Enum):
    POLISH = "POLISH"
    FORMAT = "FORMAT"
    PARSE = "PARSE"

class TaskStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
