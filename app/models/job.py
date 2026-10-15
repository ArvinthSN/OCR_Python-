from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.claim import HealthClaimData
from app.models.document import ProcessedDocument

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProgressStats(BaseModel):
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_pages: int = 0
    completed_pages: int = 0
    failed_pages: int = 0
    retried_pages: int = 0
    fields_extracted: int = 0
    fields_needs_review: int = 0
    percentage: int = 0
    current_action: str = "Initialized"

class ProcessingJob(BaseModel):
    job_id: str
    owner_id: str = "default_user"
    created_at: str
    updated_at: str
    status: JobStatus = JobStatus.QUEUED
    progress: ProgressStats = Field(default_factory=ProgressStats)
    documents: List[ProcessedDocument] = Field(default_factory=list)
    result_claim: Optional[HealthClaimData] = None
    error_message: Optional[str] = None

class FieldCorrection(BaseModel):
    field_name: str
    new_value: Any
    reason: Optional[str] = "Manual user edit"

class ValidateClaimRequest(BaseModel):
    job_id: str
    corrections: List[FieldCorrection] = Field(default_factory=list)
    confirm: bool = False
    confirmed_by: Optional[str] = "claims_adjuster"

class ValidateClaimResponse(BaseModel):
    job_id: str
    success: bool
    message: str
    claim: HealthClaimData
