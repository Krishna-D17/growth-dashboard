import enum


class SocialPlatform(str, enum.Enum):
    INSTAGRAM = "instagram"
    X = "x"
    FACEBOOK = "facebook"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class CollectionSchedule(str, enum.Enum):
    MANUAL = "manual"
    EVERY_6_HOURS = "every_6_hours"
    EVERY_12_HOURS = "every_12_hours"
    DAILY = "daily"
