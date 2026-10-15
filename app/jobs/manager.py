import os
import cv2
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from app.config import settings
from app.models.job import ProcessingJob, JobStatus, ProgressStats, FieldCorrection
from app.models.document import ProcessedDocument, DocumentPage, ProcessingStatus, DocumentType
from app.models.ocr import OCRResult, ExtractionMethod
from app.models.claim import HealthClaimData
from app.models.fields import FieldStatus
from app.pdf.processor import PDFProcessor
from app.preprocessing.pipeline import PreprocessingPipeline
from app.ocr.engine import OCREngine
from app.ocr.easyocr_adapter import EasyOCRAdapter
from app.ocr.mock_adapter import MockOCREngine
from app.ocr.targeted_ocr import TargetedFieldOCR
from app.classification.classifier import DocumentClassifier
from app.extraction.claim_extractor import ClaimExtractor
from app.merging.merger import DocumentMerger

class JobManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(JobManager, cls).__new__(cls)
                    cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.jobs: Dict[str, ProcessingJob] = {}
        self.jobs_lock = threading.Lock()
        self.pdf_processor = PDFProcessor()
        self.pipeline = PreprocessingPipeline()
        self.classifier = DocumentClassifier()
        self.extractor = ClaimExtractor()
        self.merger = DocumentMerger()
        self.ocr_engine: Optional[OCREngine] = None

    def get_ocr_engine(self) -> OCREngine:
        if self.ocr_engine is None:
            # Use EasyOCRAdapter by default
            self.ocr_engine = EasyOCRAdapter()
        return self.ocr_engine

    def set_ocr_engine(self, engine: OCREngine):
        self.ocr_engine = engine

    def create_job(self, job_id: str, owner_id: str = "default_user") -> ProcessingJob:
        now = datetime.utcnow().isoformat()
        job = ProcessingJob(
            job_id=job_id,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            status=JobStatus.QUEUED,
            progress=ProgressStats(current_action="Job queued for processing")
        )
        with self.jobs_lock:
            self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        with self.jobs_lock:
            return self.jobs.get(job_id)

    def add_documents_to_job(self, job_id: str, docs: List[ProcessedDocument]):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if job:
                job.documents.extend(docs)
                job.progress.total_files = len(job.documents)
                job.updated_at = datetime.utcnow().isoformat()

    def start_processing_async(self, job_id: str):
        thread = threading.Thread(target=self._process_job, args=(job_id,), daemon=True)
        thread.start()

    def _process_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job or job.status == JobStatus.PROCESSING:
            return

        job.status = JobStatus.PROCESSING
        job.progress.current_action = "Starting document processing pipeline"
        job.updated_at = datetime.utcnow().isoformat()

        engine = self.get_ocr_engine()
        doc_ocr_results: Dict[str, List[Tuple[DocumentPage, Optional[OCRResult]]]] = {}
        doc_types_map: Dict[str, DocumentType] = {}

        try:
            total_pages = 0
            # Pre-calculate estimated pages
            for doc in job.documents:
                stored_file = settings.UPLOAD_DIR / doc.sanitized_filename
                if doc.file_type == "pdf":
                    import fitz
                    try:
                        with fitz.open(stored_file) as f_pdf:
                            doc.page_count = len(f_pdf)
                            total_pages += len(f_pdf)
                    except Exception:
                        doc.page_count = 1
                        total_pages += 1
                else:
                    doc.page_count = 1
                    total_pages += 1

            job.progress.total_pages = max(1, total_pages)

            # Process each document
            for doc_idx, doc in enumerate(job.documents, start=1):
                job.progress.current_action = f"Processing document {doc_idx}/{len(job.documents)}: {doc.original_filename}"
                stored_file = settings.UPLOAD_DIR / doc.sanitized_filename
                pages_and_ocr: List[Tuple[DocumentPage, Optional[OCRResult]]] = []
                doc_full_text = []

                if doc.file_type == "pdf":
                    # Process PDF
                    pdf_results = self.pdf_processor.process_pdf(str(stored_file), doc.original_filename)
                    for page, direct_ocr in pdf_results:
                        if direct_ocr is not None:
                            # Digital PDF page with high confidence text
                            pages_and_ocr.append((page, direct_ocr))
                            doc_full_text.append(direct_ocr.full_text)
                            job.progress.completed_pages += 1
                        else:
                            # Scanned PDF page needing image enhancement & OCR
                            ocr_res = self._enhance_and_ocr_page(page, engine)
                            pages_and_ocr.append((page, ocr_res))
                            if ocr_res:
                                doc_full_text.append(ocr_res.full_text)
                            job.progress.completed_pages += 1

                elif doc.file_type in ("png", "jpeg", "tiff"):
                    # Process Image
                    page = DocumentPage(
                        page_number=1,
                        source_filename=doc.original_filename,
                        original_image_path=str(stored_file),
                        status=ProcessingStatus.PROCESSING
                    )
                    ocr_res = self._enhance_and_ocr_page(page, engine)
                    pages_and_ocr.append((page, ocr_res))
                    if ocr_res:
                        doc_full_text.append(ocr_res.full_text)
                    job.progress.completed_pages += 1

                # Classify document
                combined_text = "\n".join(doc_full_text)
                doc_type, conf, evidence = self.classifier.classify(combined_text)
                doc.classification = doc_type
                doc.classification_confidence = conf
                doc.classification_evidence = evidence
                doc.pages = [p for p, _ in pages_and_ocr]
                doc.status = ProcessingStatus.COMPLETED

                doc_ocr_results[doc.document_id] = pages_and_ocr
                doc_types_map[doc.original_filename] = doc_type

                job.progress.completed_files += 1
                job.progress.percentage = int((job.progress.completed_pages / max(1, job.progress.total_pages)) * 80)
                job.updated_at = datetime.utcnow().isoformat()

            # Structured Claim Extraction
            job.progress.current_action = "Extracting health claim fields and reconstructing line items"
            claim_data = self.extractor.extract_from_documents(job.documents, doc_ocr_results)

            # Multi-document merging & cross-document consistency
            job.progress.current_action = "Merging multi-document evidence and verifying consistency"
            merged_claim = self.merger.merge_claims(claim_data, doc_types_map)

            job.result_claim = merged_claim
            job.progress.fields_extracted = len(merged_claim.fields)
            job.progress.fields_needs_review = sum(1 for f in merged_claim.fields.values() if f.status != FieldStatus.EXTRACTED)
            job.progress.percentage = 100
            job.progress.current_action = "Processing successfully completed"
            job.status = JobStatus.COMPLETED
            job.updated_at = datetime.utcnow().isoformat()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = f"Processing error: {str(e)}"
            job.progress.current_action = f"Failed: {str(e)}"
            job.updated_at = datetime.utcnow().isoformat()

    def _enhance_and_ocr_page(self, page: DocumentPage, engine: OCREngine) -> Optional[OCRResult]:
        """
        Enhances a page image (orientation, deskew, deblur, CLAHE) and executes OCR.
        Saves enhanced image for frontend before/after comparison.
        """
        orig_path = page.original_image_path
        if not orig_path or not os.path.exists(orig_path):
            return None

        # Execute preprocessing pipeline
        enhanced_img, metrics, records = self.pipeline.process_image(orig_path)
        page.quality_metrics = metrics
        page.transformations_applied = records
        page.detected_rotation = metrics.detected_rotation
        page.deskew_angle = metrics.skew_angle

        # Save enhanced image for preview
        enh_path = Path(orig_path).parent / f"page_{page.page_number}_enhanced.png"
        cv2.imwrite(str(enh_path), enhanced_img)
        page.enhanced_image_path = str(enh_path)
        page.width = enhanced_img.shape[1]
        page.height = enhanced_img.shape[0]

        # Determine OCR profile
        profile = "blurred" if metrics.is_blurred else "default"
        if metrics.contrast_score < settings.CONTRAST_LOW_THRESHOLD:
            profile = "low_contrast"

        page.ocr_profile_used = profile

        # Run OCR
        enhancements_list = [r.step for r in records]
        ocr_res = engine.recognize(
            enhanced_img,
            profile=profile,
            page_number=page.page_number,
            extraction_method=ExtractionMethod.OCR_AFTER_ENHANCEMENT,
            rotation_applied=metrics.detected_rotation,
            enhancement_applied=enhancements_list
        )

        page.raw_text = ocr_res.full_text
        page.status = ProcessingStatus.COMPLETED
        return ocr_res

    def apply_corrections(self,
                          job_id: str,
                          corrections: List[FieldCorrection],
                          confirm: bool = False,
                          confirmed_by: Optional[str] = "claims_adjuster") -> Optional[HealthClaimData]:
        """
        Applies user corrections and records confirmation without restarting processing.
        """
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job or not job.result_claim:
                return None

            claim = job.result_claim
            for corr in corrections:
                fld = claim.fields.get(corr.field_name)
                if fld:
                    old_v = fld.value
                    fld.value = corr.new_value
                    fld.normalized_value = corr.new_value
                    fld.status = FieldStatus.EXTRACTED
                    fld.warning_message = None
                    fld.recommended_action = None
                    claim.audit_trail.append({
                        "action": "user_manual_correction",
                        "field": corr.field_name,
                        "old_value": old_v,
                        "new_value": corr.new_value,
                        "reason": corr.reason,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    # Update summary if mapped
                    if corr.field_name == "patient_name":
                        if corr.new_value not in (None, ""):
                            claim.summary.name = str(corr.new_value)
                    elif corr.field_name in ("policy_number", "member_id"):
                        if corr.new_value not in (None, ""):
                            claim.summary.id = str(corr.new_value)
                    elif corr.field_name == "total_bill_amount":
                        try:
                            v = str(corr.new_value).replace(",", "").replace("Rs.", "").strip()
                            if v:
                                claim.summary.billed = float(v)
                        except (ValueError, TypeError):
                            pass
                    elif corr.field_name == "hospital_name":
                        if corr.new_value not in (None, ""):
                            claim.summary.hospital_name = str(corr.new_value)
                    elif corr.field_name == "admission_date":
                        if corr.new_value not in (None, ""):
                            claim.summary.admission_date = str(corr.new_value)
                    elif corr.field_name == "discharge_date":
                        if corr.new_value not in (None, ""):
                            claim.summary.discharge_date = str(corr.new_value)

            if confirm:
                claim.is_confirmed = True
                claim.confirmed_by = confirmed_by
                claim.confirmed_at = datetime.utcnow().isoformat()
                claim.summary.status = "Confirmed & Approved"
                claim.summary.stage_status = "Ready for Settlement"
                claim.audit_trail.append({
                    "action": "claim_confirmed",
                    "confirmed_by": confirmed_by,
                    "timestamp": claim.confirmed_at
                })

            job.updated_at = datetime.utcnow().isoformat()
            return claim
