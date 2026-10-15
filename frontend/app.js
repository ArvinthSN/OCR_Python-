let currentJobId = null;
let currentClaim = null;
let selectedFiles = [];

// DOM Elements
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const selectedFilesList = document.getElementById("selected-files-list");
const btnUpload = document.getElementById("btn-upload");
const progressContainer = document.getElementById("progress-container");
const progressBar = document.getElementById("progress-bar");
const progressPct = document.getElementById("progress-pct");
const progressAction = document.getElementById("progress-action");
const statFiles = document.getElementById("stat-files");
const statPages = document.getElementById("stat-pages");
const statExtracted = document.getElementById("stat-extracted");

// Dashboard Elements
const summaryDashboard = document.getElementById("summary-dashboard");
const detailedFormSection = document.getElementById("detailed-form-section");
const lineItemsSection = document.getElementById("line-items-section");
const documentPagesSection = document.getElementById("document-pages-section");

const cardPatientName = document.getElementById("card-patient-name");
const cardId = document.getElementById("card-id");
const cardPriorityType = document.getElementById("card-priority-type");
const cardAgeSla = document.getElementById("card-age-sla");
const cardHospitalName = document.getElementById("card-hospital-name");
const cardAdmissionName = document.getElementById("card-admission-name");
const cardDates = document.getElementById("card-dates");
const cardSource = document.getElementById("card-source");
const cardBilled = document.getElementById("card-billed");
const cardStageAssignee = document.getElementById("card-stage-assignee");
const cardReceived = document.getElementById("card-received");
const claimOverallStatus = document.getElementById("claim-overall-status");
const flagBanner = document.getElementById("flag-banner");
const flagReasonsList = document.getElementById("flag-reasons-list");

// Action buttons
const btnExportJson = document.getElementById("btn-export-json");
const btnConfirmClaim = document.getElementById("btn-confirm-claim");
const btnSaveCorrections = document.getElementById("btn-save-corrections");

// Modal
const imageModal = document.getElementById("image-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const modalTitle = document.getElementById("modal-title");
const modalEnhInfo = document.getElementById("modal-enhancement-info");
const modalImgOrig = document.getElementById("modal-img-orig");
const modalImgEnh = document.getElementById("modal-img-enh");

// Drag & drop listeners
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    handleFilesSelected(e.dataTransfer.files);
  }
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleFilesSelected(e.target.files);
  }
});

function handleFilesSelected(fileList) {
  selectedFiles = Array.from(fileList);
  selectedFilesList.innerHTML = "";
  selectedFiles.forEach((f) => {
    const chip = document.createElement("div");
    chip.className = "file-chip";
    chip.textContent = `📄 ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
    selectedFilesList.appendChild(chip);
  });
  btnUpload.disabled = selectedFiles.length === 0;
}

// Upload & Process
btnUpload.addEventListener("click", async () => {
  if (selectedFiles.length === 0) return;

  btnUpload.disabled = true;
  progressContainer.classList.remove("hidden");
  progressBar.style.width = "5%";
  progressPct.textContent = "5%";
  progressAction.textContent = "Uploading document files...";

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append("files", file));

  try {
    const uploadRes = await fetch("/api/documents/upload", {
      method: "POST",
      body: formData,
    });
    if (!uploadRes.ok) {
      const err = await uploadRes.json();
      throw new Error(err.detail || "Upload failed");
    }

    const uploadData = await uploadRes.json();
    currentJobId = uploadData.job_id;

    // Trigger processing
    progressAction.textContent = "Initiating OCR & document enhancement...";
    const startForm = new FormData();
    startForm.append("job_id", currentJobId);

    await fetch("/api/documents/process", {
      method: "POST",
      body: startForm,
    });

    pollJobStatus(currentJobId);
  } catch (err) {
    progressAction.textContent = `Error: ${err.message}`;
    progressBar.style.backgroundColor = "var(--danger)";
    btnUpload.disabled = false;
  }
});

// Polling
async function pollJobStatus(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/documents/jobs/${jobId}`);
      if (!res.ok) return;

      const data = await res.json();
      const p = data.progress;

      progressBar.style.width = `${p.percentage}%`;
      progressPct.textContent = `${p.percentage}%`;
      progressAction.textContent = p.current_action;
      statFiles.textContent = `Files: ${p.completed_files}/${p.total_files}`;
      statPages.textContent = `Pages: ${p.completed_pages}/${p.total_pages}`;
      statExtracted.textContent = `Fields: ${p.fields_extracted}`;

      if (data.status === "completed") {
        clearInterval(interval);
        loadResults(jobId);
      } else if (data.status === "failed") {
        clearInterval(interval);
        progressBar.style.backgroundColor = "var(--danger)";
        progressAction.textContent = `Processing failed: ${data.error_message}`;
      }
    } catch (e) {
      console.error(e);
    }
  }, 1000);
}

// Load and render results
async function loadResults(jobId) {
  const res = await fetch(`/api/documents/results/${jobId}`);
  if (!res.ok) return;
  const data = await res.json();
  currentClaim = data.claim;

  // Fetch files/pages info for before/after view
  const filesRes = await fetch(`/api/documents/files/${jobId}`);
  const filesData = await filesRes.json();

  renderSummary(currentClaim.summary);
  renderDetailedForm(currentClaim.fields);
  renderLineItems(currentClaim.line_items);
  renderPagesList(filesData.files);

  summaryDashboard.classList.remove("hidden");
  detailedFormSection.classList.remove("hidden");
  lineItemsSection.classList.remove("hidden");
  documentPagesSection.classList.remove("hidden");

  btnExportJson.disabled = false;
  btnConfirmClaim.disabled = false;
}

// Render Summary Cards
function renderSummary(summary) {
  cardPatientName.textContent = summary.name || "—";
  cardId.textContent = summary.id || "—";
  cardPriorityType.textContent = summary.priority_type || "Standard";
  cardAgeSla.textContent = `${summary.age ? summary.age + " yrs" : "—"} / ${summary.sla}`;
  cardHospitalName.textContent = summary.hospital_name || "—";
  cardAdmissionName.textContent = summary.admission_name || "—";
  cardDates.textContent = `${summary.admission_date || "—"} to ${summary.discharge_date || "—"}`;
  cardSource.textContent = summary.source || "—";
  cardBilled.textContent = `₹ ${Number(summary.billed).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  cardStageAssignee.textContent = `${summary.stage_status} (${summary.assignee})`;
  cardReceived.textContent = summary.received || "—";

  // Status Badge
  claimOverallStatus.textContent = summary.status;
  if (summary.status.includes("Auto-Accepted") || summary.status.includes("Confirmed")) {
    claimOverallStatus.className = "badge badge-success";
  } else if (summary.status.includes("Flagged")) {
    claimOverallStatus.className = "badge badge-danger";
  } else {
    claimOverallStatus.className = "badge badge-warning";
  }

  // Flags Banner
  if (summary.flagged && summary.flag_reasons.length > 0) {
    flagBanner.classList.remove("hidden");
    flagReasonsList.innerHTML = "";
    summary.flag_reasons.forEach((r) => {
      const li = document.createElement("li");
      li.textContent = r;
      flagReasonsList.appendChild(li);
    });
  } else {
    flagBanner.classList.add("hidden");
  }
}

// Render Detailed Form
function renderDetailedForm(fields) {
  const medGrid = document.getElementById("medical-fields-grid");
  const billGrid = document.getElementById("billing-fields-grid");
  const idGrid = document.getElementById("identity-fields-grid");

  medGrid.innerHTML = "";
  billGrid.innerHTML = "";
  idGrid.innerHTML = "";

  const medicalKeys = ["patient_name", "patient_age", "patient_gender", "hospital_name", "admission_name", "admission_date", "discharge_date", "diagnosis", "icd10_code", "procedure_name"];
  const billingKeys = ["policy_number", "member_id", "total_bill_amount", "claimed_amount", "bill_number"];
  const identityKeys = ["account_holder_name", "bank_account_number", "ifsc_code", "bank_name", "id_proof_number"];

  for (const [key, fld] of Object.entries(fields)) {
    const group = document.createElement("div");
    group.className = "field-group";

    const label = document.createElement("label");
    label.textContent = fld.display_name;

    const input = document.createElement("input");
    input.type = "text";
    input.className = "field-input";
    input.id = `input-field-${key}`;
    input.value = fld.display_value !== undefined && fld.display_value !== null ? fld.display_value : (fld.value || "");

    group.appendChild(label);
    group.appendChild(input);

    if (fld.warning_message) {
      const warn = document.createElement("div");
      warn.className = "field-warning";
      warn.textContent = `⚠️ ${fld.warning_message}`;
      group.appendChild(warn);
    }

    if (medicalKeys.includes(key)) {
      medGrid.appendChild(group);
    } else if (billingKeys.includes(key)) {
      billGrid.appendChild(group);
    } else {
      idGrid.appendChild(group);
    }
  }
}

// Render Line Items Table
function renderLineItems(items) {
  const tbody = document.getElementById("line-items-tbody");
  const totalEl = document.getElementById("line-items-total");
  tbody.innerHTML = "";

  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No itemized breakdown extracted.</td></tr>`;
    totalEl.textContent = "Total: ₹0.00";
    return;
  }

  let totalSum = 0;
  items.forEach((item, idx) => {
    totalSum += Number(item.amount) || 0;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td><strong>${item.description}</strong></td>
      <td>${item.quantity}</td>
      <td>₹${Number(item.unit_rate).toFixed(2)}</td>
      <td><strong>₹${Number(item.amount).toFixed(2)}</strong></td>
      <td><span class="badge badge-success">Extracted</span></td>
    `;
    tbody.appendChild(tr);
  });

  totalEl.textContent = `Total: ₹${totalSum.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

// Render Document Pages list
function renderPagesList(files) {
  const container = document.getElementById("pages-list-container");
  container.innerHTML = "";

  files.forEach((file) => {
    const card = document.createElement("div");
    card.style.border = "1px solid var(--border)";
    card.style.borderRadius = "var(--radius)";
    card.style.padding = "12px 16px";
    card.style.marginBottom = "10px";
    card.style.background = "#ffffff";

    let pagesHtml = file.pages
      .map(
        (p) => `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 13px;">
        <span>Page ${p.page_number} | Rotation: ${p.detected_rotation}° | Deskew: ${p.deskew_angle.toFixed(1)}° | Profile: ${p.ocr_profile || "default"}</span>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="viewPageModal('${file.filename}', ${p.page_number}, '${p.transformations.join(", ")}')">🖼️ View Before & After</button>
      </div>
    `
      )
      .join("");

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <strong>📄 ${file.filename}</strong>
        <span class="badge badge-info">${file.classification.replace("_", " ").toUpperCase()}</span>
      </div>
      <div>${pagesHtml}</div>
    `;
    container.appendChild(card);
  });
}

// Modal open/close
window.viewPageModal = function (filename, pageNum, transforms) {
  const stem = filename.replace(/\.[^/.]+$/, "");
  modalTitle.textContent = `${filename} (Page ${pageNum})`;
  modalEnhInfo.textContent = `Transformations applied: ${transforms || "None"}`;
  modalImgOrig.src = `/data/processed/${stem}/page_${pageNum}_orig.png`;
  modalImgEnh.src = `/data/processed/${stem}/page_${pageNum}_enhanced.png`;
  imageModal.style.display = "flex";
};

btnCloseModal.addEventListener("click", () => {
  imageModal.style.display = "none";
});

// Save edits
btnSaveCorrections.addEventListener("click", async () => {
  if (!currentJobId) return;

  const corrections = [];
  const inputs = document.querySelectorAll("[id^='input-field-']");
  inputs.forEach((inp) => {
    const fieldName = inp.id.replace("input-field-", "");
    corrections.push({
      field_name: fieldName,
      new_value: inp.value,
      reason: "Manual correction via web UI",
    });
  });

  const res = await fetch("/api/documents/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_id: currentJobId,
      corrections: corrections,
      confirm: false,
    }),
  });

  if (res.ok) {
    const data = await res.json();
    currentClaim = data.claim;
    renderSummary(currentClaim.summary);
    alert("Field updates saved successfully.");
  }
});

// Confirm Claim
btnConfirmClaim.addEventListener("click", async () => {
  if (!currentJobId) return;

  const res = await fetch("/api/documents/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_id: currentJobId,
      corrections: [],
      confirm: true,
      confirmed_by: "Claims Adjuster",
    }),
  });

  if (res.ok) {
    const data = await res.json();
    currentClaim = data.claim;
    renderSummary(currentClaim.summary);
    alert("Claim verified and confirmed!");
  }
});

// Export JSON
btnExportJson.addEventListener("click", () => {
  if (!currentJobId) return;
  window.location.href = `/api/documents/export/${currentJobId}`;
});
