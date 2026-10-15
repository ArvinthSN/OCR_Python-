import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.jobs.manager import JobManager
from app.ocr.mock_adapter import MockOCREngine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_mock_engine():
    # Use mock engine in API test to avoid heavy ML model loading delays
    jm = JobManager()
    jm.set_ocr_engine(MockOCREngine())

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["ocr_available"] is True

def test_full_api_workflow(tmp_path):
    # 1. Upload
    # Create valid synthetic PNG bytes using cv2
    import cv2
    import numpy as np
    valid_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.putText(valid_img, "TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    _, encoded = cv2.imencode(".png", valid_img)
    png_bytes = encoded.tobytes()

    file_upload = ("claim_doc.png", io.BytesIO(png_bytes), "image/png")

    upload_res = client.post("/api/documents/upload", files={"files": file_upload})
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    job_id = upload_data["job_id"]
    assert job_id.startswith("job_")

    # 2. Start Processing
    proc_res = client.post("/api/documents/process", data={"job_id": job_id})
    assert proc_res.status_code == 200

    # Wait for job completion synchronously (with mock engine it completes quickly)
    import time
    for _ in range(20):
        job_res = client.get(f"/api/documents/jobs/{job_id}")
        assert job_res.status_code == 200
        if job_res.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.3)

    final_job = client.get(f"/api/documents/jobs/{job_id}").json()
    assert final_job["status"] == "completed"

    # 3. Check Results
    results_res = client.get(f"/api/documents/results/{job_id}")
    assert results_res.status_code == 200
    res_data = results_res.json()
    assert res_data["claim"] is not None
    assert "summary" in res_data["claim"]

    # 4. Check Files and Preprocessing Metadata
    files_res = client.get(f"/api/documents/files/{job_id}")
    assert files_res.status_code == 200
    files_data = files_res.json()
    assert len(files_data["files"]) == 1

    # 5. Validate & Apply User Correction
    val_payload = {
        "job_id": job_id,
        "corrections": [
            {"field_name": "patient_name", "new_value": "Arjun Sharma Edited"}
        ],
        "confirm": True,
        "confirmed_by": "Senior Claims Officer"
    }
    val_res = client.post("/api/documents/validate", json=val_payload)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["claim"]["summary"]["name"] == "Arjun Sharma Edited"
    assert val_data["claim"]["is_confirmed"] is True

    # 6. Export JSON
    exp_res = client.get(f"/api/documents/export/{job_id}")
    assert exp_res.status_code == 200
    assert "application/json" in exp_res.headers["content-type"]
