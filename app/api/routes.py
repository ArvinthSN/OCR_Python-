import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from app.models.fields import FieldStatus

from app.config import settings
from app.ingestion.service import IngestionService, IngestionError
from app.jobs.manager import JobManager
from app.models.job import (
    ProcessingJob, JobStatus, ValidateClaimRequest, ValidateClaimResponse
)

router = APIRouter(prefix="/api", tags=["documents"])
ingestion_service = IngestionService()
job_manager = JobManager()

@router.get("/health")
def get_health():
    """Application health endpoint with OCR engine status."""
    engine = job_manager.get_ocr_engine()
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "primary_engine": settings.OCR_PRIMARY_ENGINE,
        "ocr_available": engine.is_available(),
        "gpu_available": settings.OCR_USE_GPU
    }

@router.post("/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    owner_id: str = Form("default_user")
):
    """
    Accepts ZIP archives, PDFs, or images.
    Performs cross-platform magic byte validation, zip safety checks, and creates a job.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = job_manager.create_job(job_id, owner_id)

    total_uploaded = 0
    all_processed_docs = []

    for file in files:
        # Check overall size
        temp_dest = settings.TEMP_DIR / f"upload_{uuid.uuid4().hex[:8]}_{file.filename}"
        with open(temp_dest, "wb") as buffer:
            size = 0
            while content := await file.read(1024 * 1024):  # 1MB chunks
                size += len(content)
                total_uploaded += len(content)
                if total_uploaded > settings.MAX_UPLOAD_SIZE_BYTES:
                    temp_dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Upload exceeds max total size limit.")
                buffer.write(content)

        try:
            processed_docs = ingestion_service.process_uploaded_file(str(temp_dest), file.filename)
            all_processed_docs.extend(processed_docs)
        except IngestionError as e:
            # File validation error
            temp_dest.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            temp_dest.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Failed to ingest {file.filename}: {str(e)}")
        finally:
            temp_dest.unlink(missing_ok=True)

    job_manager.add_documents_to_job(job_id, all_processed_docs)

    return {
        "job_id": job_id,
        "message": f"Successfully ingested {len(all_processed_docs)} document(s).",
        "documents": [
            {
                "document_id": d.document_id,
                "original_filename": d.original_filename,
                "file_type": d.file_type,
                "size_bytes": d.file_size_bytes
            }
            for d in all_processed_docs
        ]
    }

@router.post("/documents/process")
async def start_process(job_id: str = Form(...)):
    """
    Starts asynchronous document processing for a job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status == JobStatus.PROCESSING:
        return {"job_id": job_id, "status": job.status, "message": "Job is already processing."}

    job_manager.start_processing_async(job_id)

    return {
        "job_id": job_id,
        "status": JobStatus.PROCESSING,
        "message": "Processing started in background."
    }

@router.get("/documents/jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Returns current status and fine-grained progress metrics.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress.dict(),
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }

@router.get("/documents/results/{job_id}")
def get_job_results(job_id: str):
    """
    Returns structured claim fields, summary indicators, line items, and audit trail.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != JobStatus.COMPLETED or not job.result_claim:
        return {
            "job_id": job.job_id,
            "status": job.status,
            "claim": None,
            "message": "Processing not completed yet."
        }

    return {
        "job_id": job.job_id,
        "status": job.status,
        "claim": job.result_claim.dict()
    }

@router.get("/documents/files/{job_id}")
def get_job_files(job_id: str):
    """
    Returns per-file and per-page status, applied orientation and enhancements.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    files_info = []
    for doc in job.documents:
        pages_info = []
        for p in doc.pages:
            pages_info.append({
                "page_number": p.page_number,
                "is_digital_pdf": p.is_digital_pdf_page,
                "detected_rotation": p.detected_rotation,
                "deskew_angle": p.deskew_angle,
                "ocr_profile": p.ocr_profile_used,
                "transformations": [t.step for t in p.transformations_applied],
                "quality_metrics": p.quality_metrics.dict() if p.quality_metrics else None,
                "has_enhanced_image": bool(p.enhanced_image_path and os.path.exists(p.enhanced_image_path))
            })

        files_info.append({
            "document_id": doc.document_id,
            "filename": doc.original_filename,
            "file_type": doc.file_type,
            "classification": doc.classification,
            "classification_confidence": doc.classification_confidence,
            "classification_evidence": doc.classification_evidence,
            "status": doc.status,
            "pages": pages_info
        })

    return {"job_id": job.job_id, "files": files_info}

@router.post("/documents/validate", response_model=ValidateClaimResponse)
def validate_and_edit_claim(req: ValidateClaimRequest):
    """
    Validates field values, applies manual user edits, and optionally confirms the claim.
    """
    updated_claim = job_manager.apply_corrections(
        req.job_id, req.corrections, confirm=req.confirm, confirmed_by=req.confirmed_by
    )
    if not updated_claim:
        raise HTTPException(status_code=404, detail="Job or claim not found.")

    return ValidateClaimResponse(
        job_id=req.job_id,
        success=True,
        message="Claim updated successfully.",
        claim=updated_claim
    )

@router.get("/documents/export/{job_id}")
def export_claim_json(job_id: str):
    """
    Exports clean JSON representation of autofilled claim data.
    """
    job = job_manager.get_job(job_id)
    if not job or not job.result_claim:
        raise HTTPException(status_code=404, detail="Processed claim not found.")

    return JSONResponse(
        content=job.result_claim.dict(),
        headers={"Content-Disposition": f"attachment; filename=claim_{job_id}.json"}
        )
    
@router.get("/documents/export_clean/{job_id}")
def export_clean_claim_json(job_id: str):
    """Return only fields with status == EXTRACTED and confidence >= accept threshold."""
    job = job_manager.get_job(job_id)
    if not job or not job.result_claim:
        raise HTTPException(status_code=404, detail="Processed claim not found.")
    # Deep copy to avoid mutating original
    claim = job.result_claim.copy()
    # Filter fields
    clean_fields = {
        k: v
        for k, v in claim.fields.items()
        if v.status == FieldStatus.EXTRACTED and v.confidence >= settings.OCR_CONFIDENCE_THRESHOLD_ACCEPT
    }
    claim.fields = clean_fields
    # Filter line items
    claim.line_items = [
        li for li in claim.line_items if li.confidence >= settings.OCR_CONFIDENCE_THRESHOLD_ACCEPT
    ]
    return JSONResponse(content=claim.dict())
