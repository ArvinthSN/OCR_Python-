# Universal Health Claim OCR, Image Enhancement & Autofill System

A production-ready document ingestion, image enhancement, orientation correction, and structured field extraction system specifically tailored for **health insurance claims**.

Users upload ZIP archives (including nested folders and nested archives), PDFs (digital or scanned), or photographed documents (including blurred, noisy, and rotated images). The system automatically discovers files, normalizes orientation, enhances recoverable text, extracts medical and billing data using layout-aware EasyOCR, performs deterministic domain validation, and populates a clear claim review form.

---

## 🌟 Key Capabilities

1. **Accuracy on Rotated & Blurred Images**:
   - **Layered Orientation**: Corrects EXIF, coarse 90°/180°/270° orientation, fine deskew ($\pm 45^\circ$) with content-preserving borders, and document quadrilateral perspective warping.
   - **Selective Deblurring**: Distinguishes directional motion blur from defocus blur via gradient anisotropy; applies regularized Wiener deconvolution, linear motion kernel restoration, or conservative unsharp masking.
   - **Adaptive Rescaling**: Dynamically rescales low-resolution text boxes towards optimal recognizer heights (~32px).
   - **Field-Targeted Re-OCR**: Re-crops high-value fields (Policy Number, IFSC, Dates, Amounts), enhances the crop, and re-runs OCR with constrained character allowlists.

2. **Trustworthiness & Calibration**:
   - **False Acceptance Target**: Precision-first design. Unreadable or low-confidence characters are flagged with actionable inline warnings instead of being fabricated or hallucinated.
   - **Context-Restricted Character Correction**: Corrects confusions (e.g., `O` $\leftrightarrow$ `0`, `l`/`I` $\leftrightarrow$ `1`, `S` $\leftrightarrow$ `5`) strictly in numeric/alphanumeric code contexts with an auditable replacement trail.

3. **Domain-Specific Validation Rules**:
   - **12-digit Aadhaar Checksum**: Verhoeff algorithm verification with automatic masking (`XXXX-XXXX-1234`).
   - **IFSC & PAN**: Deterministic regular expressions (`^[A-Z]{4}0[A-Z0-9]{6}$`, `^[A-Z]{5}[0-9]{4}[A-Z]$`).
   - **Dates & Amounts**: Indian locale-first date normalization to ISO (`YYYY-MM-DD`), stay consistency (`admission_date <= discharge_date`), and Indian digit grouping parsing (`1,25,000.00`).
   - **Identity Mismatch Detection**: RapidFuzz cross-document name comparison flags discrepancies between invoices, discharge summaries, and policies.

4. **Targeted Medical Claim Fields**:
   - **Summary Dashboard**: Patient Name, Member/Policy ID, Priority Types (Emergency / Urgent / Standard), Age, SLA, Hospital Name, Admission Name (Doctor), Admission Date, Discharge Date, Source, Billed Amount, Claimed Amount, Flagged status & reasons, Stage status, Assignee, Received timestamp.
   - **Line Items Table**: Itemized breakdown of hospital expenses (Description, Quantity, Unit Rate, Total Amount).

---

## 🏗️ Architecture

```
claimOCR/
├── app/
│   ├── config.py                 # Application settings, thresholds, and limits
│   ├── main.py                   # FastAPI app, static mounts, CORS
│   ├── models/                   # Pydantic schemas (documents, pages, OCR, fields, claim, jobs)
│   ├── ingestion/                # Magic bytes validation, secure ZIP extractor, upload dispatcher
│   ├── pdf/                      # PyMuPDF digital text extraction & 300 DPI page rendering
│   ├── preprocessing/            # Quality assessment, orientation (0/90/180/270), deskew, deblur, CLAHE
│   ├── ocr/                      # EasyOCR adapter, profiles, targeted field crop OCR, mock engine
│   ├── classification/           # Keyword and layout document classifier
│   ├── extraction/               # Spatial label-value association, table line items, character corrections
│   ├── validation/               # Verhoeff checksum, domain validators, warning generator
│   ├── merging/                  # Multi-document source priorities & conflict resolution
│   ├── jobs/                     # Background job manager & progress tracking
│   └── api/                      # REST endpoints (/upload, /process, /jobs, /results, /validate, /export)
├── frontend/                     # Modern responsive UI (index.html, styles.css, app.js)
├── scripts/
│   ├── download_models.py        # Pre-download and verify EasyOCR models
│   ├── synthetic_data.py         # Ground truth templates for claims
│   ├── benchmark_generator.py    # Synthetic degraded document generator
│   └── run_benchmark.py          # Benchmark runner and docs/evaluation.md generator
├── tests/                        # 31 automated tests covering ingestion, preprocessing, validation, OCR, API
└── docs/
    └── evaluation.md             # Benchmark measurement report
```

---

## 🚀 Quickstart & Installation

### Prerequisites
- **Python**: 3.10 or 3.11 (tested on Python 3.11.9 Windows 64-bit)
- **Node.js**: (Optional, static frontend is served directly by FastAPI)
- **RAM**: Minimum 4GB (8GB recommended for OCR on CPU)

### 1. Clone & Setup Virtual Environment

#### Windows (PowerShell)
```powershell
git clone <repo_url> claimOCR
cd claimOCR

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Linux / macOS (Bash)
```bash
git clone <repo_url> claimOCR
cd claimOCR

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Pre-download OCR Models (Offline Support)
To avoid downloading models during live user requests:
```bash
python scripts/download_models.py
```
This stores `craft_mlt_25k.pth` and `english_g2.pth` in `~/.EasyOCR/model/`.

---

## 🏃 Running the Application

### Start the FastAPI Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at:
👉 **`http://localhost:8000`**

### Using the Frontend:
1. **Upload Documents**: Drag and drop a ZIP archive, single/multiple PDFs, or images (JPG, PNG, TIFF) into the upload area.
2. **Process**: Click **Ingest & Process Documents**. The progress bar tracks file extraction, page rendering, enhancement, and field extraction in real time.
3. **Inspect Autofilled Claim**:
   - The top dashboard displays core fields: **Patient Name, ID, Priority Type, Age, SLA, Hospital Name, Doctor, Dates, Source, Billed Amount, Flagged Reasons, Stage, Assignee, Received Date**.
   - Check the **Itemized Hospital Expenses** table for line items.
   - Click **View Before & After** to inspect orientation and deblurring transformations.
4. **Edit & Confirm**: Make inline corrections, click **Save Edits**, or click **Confirm Claim** for final sign-off.
5. **Export**: Click **Export JSON** to download the clean structured claim data.

---

## 🧪 Running Automated Tests

Run the complete pytest test suite:
```bash
pytest -v
```

This executes 31 tests covering:
- **`test_ingestion.py`**: Magic bytes verification, spoofed files, path traversal prevention (`../../`), zip bomb limits.
- **`test_pdf.py`**: PyMuPDF digital text extraction and high-DPI rendering.
- **`test_preprocessing.py`**: Sharpness assessment, 90°/180°/270° orientation detection, deskew without cropping, Wiener deconvolution, CLAHE.
- **`test_validation.py`**: 12-digit Aadhaar Verhoeff validation, masking, IFSC, PAN, Mobile, ICD-10, date parsing, RapidFuzz name consistency.
- **`test_extraction.py`**: Spatial label-value pairing, context character correction (`l25OOO` $\rightarrow$ `125000`), table line item reconstruction.
- **`test_merging.py`**: Multi-document source priorities and identity conflict detection.
- **`test_ocr.py`**: Mock engine and targeted crop re-OCR.
- **`test_api.py`**: Full upload $\rightarrow$ process $\rightarrow$ review $\rightarrow$ edit $\rightarrow$ confirm $\rightarrow$ export workflow.

---

## 📊 Running the Degradation Benchmark

To generate realistic degraded documents (clean, 15°, 90°, 180°, 270°, Gaussian blur, motion blur, noise, low contrast, and combined) and measure exact-match field accuracy:
```bash
python -m scripts.run_benchmark
```
This produces the evaluation report at:
📄 **`docs/evaluation.md`**

---

## 🔒 Security & Privacy Considerations

1. **Archive Safety**:
   - Rejects path traversals (e.g. `../`) and absolute paths.
   - Enforces a 250 MB uncompressed limit and maximum nesting depth of 3 to prevent ZIP bombs.
   - Symlinks and device files are ignored.
2. **Magic Byte Verification**:
   - Validates file signatures cross-platform (does not rely on file extension alone or external C libraries).
3. **Data Protection (DPDP Act & HIPAA)**:
   - Aadhaar numbers and bank accounts are automatically masked in UI views and logs.
   - No patient data is sent to external LLMs or third-party cloud OCR APIs. All processing runs locally with EasyOCR.
   - Autofill never auto-submits claims; an explicit user confirmation step is enforced.
