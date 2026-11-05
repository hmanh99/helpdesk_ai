import enum


class TicketStatus(str, enum.Enum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_USER = "PENDING_USER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Priority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Channel(str, enum.Enum):
    CHATBOT = "CHATBOT"
    WEB_FORM = "WEB_FORM"


class MessageSender(str, enum.Enum):
    USER = "USER"
    BOT = "BOT"


class Intent(str, enum.Enum):
    KB_QUESTION = "KB_QUESTION"
    SIMPLE_TROUBLESHOOT = "SIMPLE_TROUBLESHOOT"
    NEEDS_DEPARTMENT = "NEEDS_DEPARTMENT"
    SMALLTALK = "SMALLTALK"
    UNCLEAR = "UNCLEAR"


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"

