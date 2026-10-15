import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Tuple
from app.config import settings
from app.ingestion.signature import detect_file_type

class SecurityException(Exception):
    pass

class SecureZipExtractor:
    def __init__(self,
                 max_extracted_size: int = settings.MAX_ZIP_EXTRACTED_BYTES,
                 max_file_count: int = settings.MAX_ARCHIVE_FILE_COUNT,
                 max_depth: int = settings.MAX_ZIP_NESTING_DEPTH):
        self.max_extracted_size = max_extracted_size
        self.max_file_count = max_file_count
        self.max_depth = max_depth

    def _is_safe_path(self, target_dir: Path, path: Path) -> bool:
        """Prevent path traversal (e.g. ../../etc/passwd or absolute paths)."""
        resolved_target = target_dir.resolve()
        resolved_path = path.resolve()
        return str(resolved_path).startswith(str(resolved_target))

    def extract(self, zip_path: str, output_dir: str, current_depth: int = 1) -> List[Tuple[str, str]]:
        """
        Recursively extracts files from a ZIP archive safely.
        Returns a list of (extracted_file_path, original_relative_path).
        """
        if current_depth > self.max_depth:
            raise SecurityException(f"Exceeded maximum zip nesting depth of {self.max_depth}")

        extracted_files: List[Tuple[str, str]] = []
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        total_extracted_bytes = 0
        file_count = 0

        with zipfile.ZipFile(zip_path, 'r') as zf:
            infolist = zf.infolist()

            # Pre-check file count
            if len(infolist) > self.max_file_count:
                raise SecurityException(f"Archive contains {len(infolist)} files, exceeding limit of {self.max_file_count}")

            for member in infolist:
                # Check for symlinks or device files in external attributes
                # High 16 bits of external_attr on POSIX systems contains file type
                is_symlink = (member.external_attr >> 16) & 0o120000 == 0o120000
                if is_symlink:
                    continue  # Ignore symlinks for security

                # Check uncompressed size
                total_extracted_bytes += member.file_size
                if total_extracted_bytes > self.max_extracted_size:
                    raise SecurityException(f"Decompressed archive size exceeds limit of {self.max_extracted_size} bytes")

                # Resolve and sanitize member path
                member_path = out_path / member.filename
                if not self._is_safe_path(out_path, member_path):
                    raise SecurityException(f"Path traversal detected in archive member: {member.filename}")

                if member.is_dir():
                    member_path.mkdir(parents=True, exist_ok=True)
                    continue

                # Ensure parent dir exists
                member_path.parent.mkdir(parents=True, exist_ok=True)

                # Extract member
                with zf.open(member) as source, open(member_path, "wb") as target:
                    shutil.copyfileobj(source, target)

                file_count += 1
                if file_count > self.max_file_count:
                    raise SecurityException(f"Extracted files exceed max limit of {self.max_file_count}")

                # Check if extracted file is itself a nested ZIP
                detected_type, _ = detect_file_type(str(member_path))
                if detected_type == "zip":
                    nested_sub_dir = member_path.parent / f"_nested_{member_path.stem}"
                    nested_results = self.extract(str(member_path), str(nested_sub_dir), current_depth + 1)
                    extracted_files.extend(nested_results)
                    try:
                        os.remove(member_path)
                    except Exception:
                        pass
                else:
                    extracted_files.append((str(member_path), member.filename))

        return extracted_files
