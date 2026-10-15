import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple
from app.config import settings
from app.ingestion.signature import detect_file_type, validate_file_signature
from app.ingestion.zip_extractor import SecureZipExtractor, SecurityException
from app.models.document import ProcessedDocument, ProcessingStatus

class IngestionError(Exception):
    pass

class IngestionService:
    def __init__(self):
        self.zip_extractor = SecureZipExtractor()

    def process_uploaded_file(self, temp_file_path: str, original_filename: str) -> List[ProcessedDocument]:
        """
        Validates and ingests an uploaded file (ZIP, PDF, Image).
        Dispatches ZIPs to secure extraction; single files to direct documents.
        Returns a list of ProcessedDocument records.
        """
        if not os.path.exists(temp_file_path):
            raise IngestionError(f"File not found: {temp_file_path}")

        file_size = os.path.getsize(temp_file_path)
        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise IngestionError(f"File {original_filename} exceeds max size limit of {settings.MAX_FILE_SIZE_BYTES} bytes")

        # Signature validation
        file_type, mime_type = detect_file_type(temp_file_path)
        if not file_type or not validate_file_signature(temp_file_path):
            raise IngestionError(
                f"File '{original_filename}' failed signature validation. Spoofed or unsupported file format."
            )

        processed_docs: List[ProcessedDocument] = []

        if file_type == "zip":
            # Extract ZIP
            extract_dir = settings.TEMP_DIR / f"zip_{uuid.uuid4().hex[:8]}"
            try:
                extracted = self.zip_extractor.extract(temp_file_path, str(extract_dir))
                for extracted_path, rel_name in extracted:
                    sub_type, sub_mime = detect_file_type(extracted_path)
                    if sub_type in ("pdf", "png", "jpeg", "tiff"):
                        doc_id = str(uuid.uuid4())
                        stored_path = settings.UPLOAD_DIR / f"{doc_id}_{Path(rel_name).name}"
                        shutil.copy2(extracted_path, stored_path)
                        processed_docs.append(
                            ProcessedDocument(
                                document_id=doc_id,
                                original_filename=rel_name,
                                sanitized_filename=stored_path.name,
                                file_type=sub_type,
                                mime_type=sub_mime or "application/octet-stream",
                                file_size_bytes=os.path.getsize(stored_path),
                                status=ProcessingStatus.PENDING
                            )
                        )
            finally:
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            # Single file (PDF or Image)
            doc_id = str(uuid.uuid4())
            sanitized_name = f"{doc_id}_{Path(original_filename).name}"
            stored_path = settings.UPLOAD_DIR / sanitized_name
            shutil.copy2(temp_file_path, stored_path)

            processed_docs.append(
                ProcessedDocument(
                    document_id=doc_id,
                    original_filename=original_filename,
                    sanitized_filename=sanitized_name,
                    file_type=file_type,
                    mime_type=mime_type or "application/octet-stream",
                    file_size_bytes=file_size,
                    status=ProcessingStatus.PENDING
                )
            )

        return processed_docs
