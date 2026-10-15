import io
import zipfile
import pytest
from pathlib import Path
from app.ingestion.signature import detect_file_type, detect_file_type_from_bytes, validate_file_signature
from app.ingestion.zip_extractor import SecureZipExtractor, SecurityException
from app.ingestion.service import IngestionService, IngestionError

def test_magic_byte_detection():
    # PDF
    assert detect_file_type_from_bytes(b"%PDF-1.4 header")[0] == "pdf"
    # PNG
    assert detect_file_type_from_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")[0] == "png"
    # JPEG
    assert detect_file_type_from_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")[0] == "jpeg"
    # TIFF
    assert detect_file_type_from_bytes(b"II*\x00\x08\x00\x00\x00")[0] == "tiff"
    # ZIP
    assert detect_file_type_from_bytes(b"PK\x03\x04\x14\x00\x00\x00")[0] == "zip"
    # Unknown / Executable
    assert detect_file_type_from_bytes(b"MZ\x90\x00\x03\x00\x00\x00")[0] is None

def test_spoofed_file_extension(tmp_path):
    # Fake exe renamed to claim.pdf
    spoofed = tmp_path / "fake_claim.pdf"
    spoofed.write_bytes(b"MZ\x90\x00\x03\x00not a real pdf")

    is_valid = validate_file_signature(str(spoofed), "pdf")
    assert is_valid is False

def test_safe_zip_extraction(tmp_path):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("claim_1.png", b"\x89PNG\r\n\x1a\nfake png data")
        zf.writestr("subfolder/claim_2.png", b"\x89PNG\r\n\x1a\nfake png data 2")

    extractor = SecureZipExtractor()
    out_dir = tmp_path / "extracted"
    extracted = extractor.extract(str(zip_path), str(out_dir))

    assert len(extracted) == 2
    for p, rel_name in extracted:
        assert Path(p).exists()

def test_zip_path_traversal_prevention(tmp_path):
    zip_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "malicious payload")

    extractor = SecureZipExtractor()
    out_dir = tmp_path / "extracted_evil"
    with pytest.raises(SecurityException):
        extractor.extract(str(zip_path), str(out_dir))

def test_zip_decompression_bomb_prevention(tmp_path):
    zip_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # 10 KB file
        zf.writestr("large.txt", b"A" * 10240)

    # Set threshold lower than 10240 bytes to trigger decompression limit
    extractor = SecureZipExtractor(max_extracted_size=5000)
    out_dir = tmp_path / "bomb_out"
    with pytest.raises(SecurityException):
        extractor.extract(str(zip_path), str(out_dir))
