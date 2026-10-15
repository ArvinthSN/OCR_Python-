from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.fields import ExtractedField, LineItem

class ClaimSummaryFields(BaseModel):
    """Core summary fields specifically required for immediate review and autofill."""
    name: Optional[str] = None
    id: Optional[str] = None  # Member ID / Policy No / Claim ID
    priority_type: str = "Standard"  # Emergency / Urgent / Standard / Planned
    age: Optional[int] = None
    sla: str = "7 Days (Standard SLA)"
    sla_days_remaining: int = 7
    hospital_name: Optional[str] = None
    admission_name: Optional[str] = None  # Treating doctor or admitting doctor
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    source: str = "Uploaded Documents"
    billed: float = 0.0  # Total billed amount
    claimed_amount: float = 0.0
    flagged: bool = False
    flag_reasons: List[str] = Field(default_factory=list)
    stage_status: str = "Extraction Completed"  # Ingestion -> Pre-Auth -> Adjudication -> Review
    status: str = "Pending Review"  # Auto-Accepted, Pending Review, Flagged, Needs Correction
    assignee: str = "TPA Claims Desk"
    received: str = ""

class HealthClaimData(BaseModel):
    claim_id: str
    created_at: str
    updated_at: str
    
    # Primary top-level summary requested
    summary: ClaimSummaryFields = Field(default_factory=ClaimSummaryFields)
    
    # Granular extracted fields grouped by domain
    fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    
    # Itemized bill line items
    line_items: List[LineItem] = Field(default_factory=list)
    
    # Warnings and actionable recommendations
    warnings: List[str] = Field(default_factory=list)
    
    # Cross-document mismatch flags
    mismatches: List[str] = Field(default_factory=list)
    
    # Complete decision audit trail
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    
    # User confirmed / edited flag
    is_confirmed: bool = False
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
