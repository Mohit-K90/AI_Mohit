from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class VideoRequest(BaseModel):
    concept_name: str
    domain: str
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    custom_requirements: Optional[str] = None

    @validator('concept_name')
    def concept_name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Concept name cannot be empty')
        return v.strip()


class VideoResponse(BaseModel):
    id: str
    concept_name: str
    domain: str
    difficulty_level: str
    s3_url: str
    duration: Optional[int]  # in seconds
    thumbnail_url: Optional[str]
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class VideoStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
