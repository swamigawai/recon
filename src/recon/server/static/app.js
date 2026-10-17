/**
 * Recon — Integration Readiness Web Client
 * Implements the 7-step developer workflow with zero invented metrics and strict human-in-the-loop approval.
 */

let currentSessionId = null;
let currentAssessment = null;
let activeContractTab = "sample";
let sampleContractsMap = {};
let mappingOverrides = {};

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  loadSampleDatasets();
  loadSampleContracts();
  bindEvents();
});

// -----------------------------------------------------------------------------
// UI Initialization & Tab Switching
// -----------------------------------------------------------------------------
function initTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      activeContractTab = tab.getAttribute("data-tab");
      const targetContent = document.getElementById(`tab-${activeContractTab}`);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });
}

function bindEvents() {
  document.getElementById("btn-assess").addEventListener("click", handleAssess);
  document.getElementById("btn-approve").addEventListener("click", handleApproveAndGenerate);
  document.getElementById("btn-copy-code").addEventListener("click", handleCopyCode);

  const sourceFileInput = document.getElementById("source-file");
  const sampleDatasetSelect = document.getElementById("sample-dataset-select");
  sourceFileInput.addEventListener("change", () => {
    if (sourceFileInput.files.length > 0) {
      sampleDatasetSelect.value = "";
    }
  });
  sampleDatasetSelect.addEventListener("change", () => {
    if (sampleDatasetSelect.value) {
      sourceFileInput.value = "";
    }
  });
}

// -----------------------------------------------------------------------------
// API Data Fetching: Preloaded Samples
// -----------------------------------------------------------------------------
async function loadSampleDatasets() {
  try {
    const res = await fetch("/api/sample-datasets");
    if (!res.ok) return;
    const datasets = await res.json();
    const select = document.getElementById("sample-dataset-select");
    datasets.forEach(ds => {
      const opt = document.createElement("option");
      opt.value = ds.id;
      opt.textContent = `${ds.file_name} (${ds.format.toUpperCase()})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed to load sample datasets:", err);
  }
}

async function loadSampleContracts() {
  try {
    const res = await fetch("/api/sample-contracts");
    if (!res.ok) return;
    const contracts = await res.json();
    const select = document.getElementById("sample-contract-select");
    contracts.forEach(c => {
      sampleContractsMap[c.id] = c;
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.contract_name} (v${c.version}) — ${c.fields_count} fields`;
      select.appendChild(opt);
    });

    select.addEventListener("change", () => {
      const selected = sampleContractsMap[select.value];
      const descBox = document.getElementById("contract-desc-box");
      if (selected) {
        descBox.textContent = selected.description || `Contract: ${selected.contract_name} with ${selected.fields_count} fields.`;
      } else {
        descBox.textContent = "";
      }
    });
  } catch (err) {
    console.error("Failed to load sample contracts:", err);
  }
}

// -----------------------------------------------------------------------------
// Step 1 & 2 -> Step 3, 4, 5: Assessment
// -----------------------------------------------------------------------------
async function handleAssess() {
  hideError();
  const sourceFileInput = document.getElementById("source-file");
  const sampleDatasetSelect = document.getElementById("sample-dataset-select");
  const contractFileInput = document.getElementById("contract-file");
  const contractTextarea = document.getElementById("contract-text");
  const sampleContractSelect = document.getElementById("sample-contract-select");

  const formData = new FormData();

  // Source selection
  if (sourceFileInput.files.length > 0) {
    formData.append("source_file", sourceFileInput.files[0]);
  } else if (sampleDatasetSelect.value) {
    formData.append("sample_dataset_id", sampleDatasetSelect.value);
  } else {
    showError("Please upload a source CSV/JSON file or select a preloaded sample dataset.");
    return;
  }

  // Contract selection based on active tab
  if (activeContractTab === "sample") {
    if (!sampleContractSelect.value) {
      showError("Please select a sample target contract or switch tabs to upload/paste.");
      return;
    }
    formData.append("sample_contract_id", sampleContractSelect.value);
  } else if (activeContractTab === "upload") {
    if (contractFileInput.files.length === 0) {
      showError("Please select a JSON target contract file to upload.");
      return;
    }
    formData.append("contract_file", contractFileInput.files[0]);
  } else if (activeContractTab === "paste") {
    if (!contractTextarea.value.trim()) {
      showError("Please paste valid JSON target contract schema.");
      return;
    }
    formData.append("contract_text", contractTextarea.value.trim());
  }

  const btn = document.getElementById("btn-assess");
  const loading = document.getElementById("assess-loading");
  btn.disabled = true;
  loading.classList.remove("hidden");

  try {
    const response = await fetch("/api/assess", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || "Assessment failed. Check your file format and contract schema.");
      return;
    }

    currentSessionId = data.session_id;
    currentAssessment = data;
    mappingOverrides = {};

    renderAssessment(data);
  } catch (err) {
    showError(`Network or server error during assessment: ${err.message}`);
  } finally {
    btn.disabled = false;
    loading.classList.add("hidden");
  }
}

// -----------------------------------------------------------------------------
// Render Assessment Results (Profile, Risks, Mappings)
// -----------------------------------------------------------------------------
function renderAssessment(data) {
  // 1. Source Profile
  document.getElementById("prof-filename").textContent = data.source.file_name;
  document.getElementById("prof-rows").textContent = Number(data.source.total_rows).toLocaleString();
  document.getElementById("prof-cols").textContent = data.source.total_columns;
  document.getElementById("prof-dupes").textContent = data.source.duplicate_rows_count;
  document.getElementById("prof-fingerprint").textContent = (data.source.fingerprint || "").slice(0, 20) + "...";
  document.getElementById("source-format-badge").textContent = data.source.format.toUpperCase();

  // 2. Contract Info
  document.getElementById("cont-name").textContent = data.contract.contract_name;
  document.getElementById("cont-fields").textContent = `${data.contract.total_fields} target fields`;
  document.getElementById("cont-desc").textContent = data.contract.description || "No description provided.";
  document.getElementById("contract-version-badge").textContent = `v${data.contract.version}`;

  // 3. Risks Findings
  renderRisks(data.risks, data.is_blocked);

  // 4. Mappings Table
  renderMappingsTable(data.proposals, data.source.columns);

  // Show Assessment Section, Hide Results Section until approved
  document.getElementById("step-assessment").classList.remove("hidden");
  document.getElementById("step-results").classList.add("hidden");
  document.getElementById("step-assessment").scrollIntoView({ behavior: "smooth" });
}

function renderRisks(risks, isBlocked) {
  const badge = document.getElementById("risk-status-badge");
  const list = document.getElementById("risk-list");
  list.innerHTML = "";

  if (isBlocked) {
    badge.className = "badge badge-danger";
    badge.textContent = "BLOCKED (CRITICAL RISKS)";
  } else if (risks.length > 0) {
    badge.className = "badge badge-warning";
    badge.textContent = "ACTION / REVIEW NEEDED";
  } else {
    badge.className = "badge badge-success";
    badge.textContent = "PASSED / LOW RISK";
  }

  if (risks.length === 0) {
    list.innerHTML = `<div class="stat-label">No high or critical pre-integration risks detected.</div>`;
    return;
  }

  risks.forEach(r => {
    const item = document.createElement("div");
    item.className = `risk-item ${r.severity.toLowerCase()}`;
    item.innerHTML = `
      <div class="risk-item-header">
        <span class="risk-name">[${r.rule_id}] ${escapeHtml(r.rule_name)}</span>
        <span class="badge ${getSeverityBadgeClass(r.severity)}">${r.severity}</span>
      </div>
      <div class="risk-detail"><strong>Affected Fields:</strong> ${escapeHtml(r.affected_fields.join(", ") || "General schema")}</div>
      <div class="risk-detail"><strong>Evidence:</strong> ${escapeHtml(r.evidence)}</div>
      <div class="risk-detail">${escapeHtml(r.explanation)}</div>
      <div class="risk-action"><strong>Suggested Action:</strong> ${escapeHtml(r.suggested_action)}</div>
    `;
    list.appendChild(item);
  });
}

function getSeverityBadgeClass(severity) {
  switch (severity.toLowerCase()) {
    case "critical":
    case "high":
      return "badge-danger";
    case "medium":
      return "badge-warning";
    default:
      return "badge-info";
  }
}

// -----------------------------------------------------------------------------
// Step 3 & 4: Field Mappings Table & Human Overrides
// -----------------------------------------------------------------------------
function renderMappingsTable(proposals, sourceColumns) {
  const tbody = document.getElementById("mappings-tbody");
  tbody.innerHTML = "";

  proposals.forEach(prop => {
    const tr = document.createElement("tr");

    // Target Field Cell
    const tdTarget = document.createElement("td");
    tdTarget.innerHTML = `
      <strong>${escapeHtml(prop.target_field)}</strong>
      ${prop.required ? '<span class="badge badge-req">REQUIRED</span>' : '<span class="badge badge-info">OPTIONAL</span>'}
      <div class="form-hint">${escapeHtml(prop.description || "")}</div>
    `;

    // Type Cell
    const tdType = document.createElement("td");
    let typeDetail = `<code class="font-mono">${escapeHtml(prop.target_type)}</code>`;
    if (prop.allowed_values && prop.allowed_values.length > 0) {
      typeDetail += `<div class="form-hint">Enum: ${escapeHtml(prop.allowed_values.slice(0, 4).join(", "))}${prop.allowed_values.length > 4 ? "..." : ""}</div>`;
    }
    if (prop.pattern) {
      typeDetail += `<div class="form-hint font-mono">/${escapeHtml(prop.pattern)}/</div>`;
    }
    tdType.innerHTML = typeDetail;

    // Source Column Mapping Select (Human Decision / Overrides)
    const tdSelect = document.createElement("td");
    const select = document.createElement("select");
    select.className = "form-select mapping-select";
    select.dataset.target = prop.target_field;
    select.dataset.required = prop.required ? "true" : "false";

    // Default Unmapped option
    const optNone = document.createElement("option");
    optNone.value = "";
    optNone.textContent = "-- Unmapped / Skip --";
    select.appendChild(optNone);

    sourceColumns.forEach(col => {
      const opt = document.createElement("option");
      opt.value = col;
      opt.textContent = col;
      if (prop.proposed_source_field === col) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    // Check if unresolved initially
    const initialVal = select.value;
    if (!initialVal && prop.required) {
      select.classList.add("highlight-unresolved");
    }

    select.addEventListener("change", e => {
      const chosen = e.target.value;
      mappingOverrides[prop.target_field] = chosen;
      if (!chosen && prop.required) {
        select.classList.add("highlight-unresolved");
      } else {
        select.classList.remove("highlight-unresolved");
      }
      updateApprovalState();
    });

    tdSelect.appendChild(select);

    // Engine Evidence Cell (Strictly Engine Reasons, No Fake Percentages)
    const tdEvidence = document.createElement("td");
    const ul = document.createElement("ul");
    ul.className = "evidence-list";
    (prop.evidence || []).forEach(ev => {
      const li = document.createElement("li");
      li.textContent = ev;
      ul.appendChild(li);
    });
    tdEvidence.appendChild(ul);

    // Status Cell
    const tdStatus = document.createElement("td");
    const isUnresolved = prop.is_unresolved || !prop.proposed_source_field;
    tdStatus.innerHTML = isUnresolved
      ? `<span class="badge badge-warning">UNRESOLVED</span>`
      : `<span class="badge badge-success">PROPOSED</span>`;

    tr.appendChild(tdTarget);
    tr.appendChild(tdType);
    tr.appendChild(tdSelect);
    tr.appendChild(tdEvidence);
    tr.appendChild(tdStatus);

    tbody.appendChild(tr);
  });

  updateApprovalState();
}

function updateApprovalState() {
  const selects = document.querySelectorAll(".mapping-select");
  let unmappedRequiredCount = 0;

  selects.forEach(sel => {
    const isRequired = sel.dataset.required === "true";
    if (isRequired && !sel.value) {
      unmappedRequiredCount++;
    }
  });

  const warningBox = document.getElementById("unresolved-warning");
  const countText = document.getElementById("unresolved-count-text");
  const btnApprove = document.getElementById("btn-approve");

  if (unmappedRequiredCount > 0) {
    warningBox.classList.remove("hidden");
    countText.textContent = `${unmappedRequiredCount} required target field${unmappedRequiredCount > 1 ? "s are" : " is"} currently unmapped.`;
    btnApprove.disabled = true;
    btnApprove.title = "All required fields must be mapped before adapter generation.";
  } else {
    warningBox.classList.add("hidden");
    btnApprove.disabled = false;
    btnApprove.title = "";
  }
}

// -----------------------------------------------------------------------------
// Step 6 & 7: Human Approval, Adapter Generation & Sandbox Validation
// -----------------------------------------------------------------------------
async function handleApproveAndGenerate() {
  hideError();
  if (!currentSessionId) {
    showError("No active assessment session. Please assess a dataset first.");
    return;
  }

  const reviewerName = document.getElementById("reviewer-name").value.trim() || "lead_engineer";

  // Harvest overrides
  const selects = document.querySelectorAll(".mapping-select");
  const overrides = {};
  for (const sel of selects) {
    const target = sel.dataset.target;
    const isReq = sel.dataset.required === "true";
    const val = sel.value.trim();
    if (isReq && !val) {
      showError(`Target field '${target}' is required but unmapped. Please select a source column.`);
      return;
    }
    if (val) {
      overrides[target] = val;
    }
  }

  const btn = document.getElementById("btn-approve");
  const loading = document.getElementById("approve-loading");
  btn.disabled = true;
  loading.classList.remove("hidden");

  try {
    const response = await fetch("/api/approve-and-generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        reviewer: reviewerName,
        overrides: overrides,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || "Approval or adapter sandbox generation failed.");
      return;
    }

    renderResults(data);
  } catch (err) {
    showError(`Error during adapter generation: ${err.message}`);
  } finally {
    btn.disabled = false;
    loading.classList.add("hidden");
  }
}

// -----------------------------------------------------------------------------
// Step 7: Render Results, Zero-Loss Accounting, Test Cases & Reports
// -----------------------------------------------------------------------------
function renderResults(data) {
  // 1. Readiness Banner
  const banner = document.getElementById("readiness-banner");
  const icon = document.getElementById("readiness-icon");
  const stateText = document.getElementById("readiness-state-text");
  const passRateBadge = document.getElementById("readiness-pass-rate-badge");
  const rationaleText = document.getElementById("readiness-rationale-text");
  const reasonsBox = document.getElementById("readiness-reasons-box");

  const state = data.readiness_state.toLowerCase();
  banner.className = `readiness-banner ${state}`;
  stateText.textContent = `READINESS: ${data.readiness_state.toUpperCase()}`;
  rationaleText.textContent = data.readiness_rationale;

  if (state === "pass") {
    icon.textContent = "✓";
    passRateBadge.className = "badge badge-success";
  } else if (state === "needs_review") {
    icon.textContent = "⚠";
    passRateBadge.className = "badge badge-warning";
  } else {
    icon.textContent = "✕";
    passRateBadge.className = "badge badge-danger";
  }
  passRateBadge.textContent = `${data.validation.contract_pass_rate}% Pass Rate`;

  reasonsBox.innerHTML = "";
  if (data.blocking_reasons && data.blocking_reasons.length > 0) {
    data.blocking_reasons.forEach(r => {
      reasonsBox.innerHTML += `<div>• <strong>Blocking:</strong> ${escapeHtml(r)}</div>`;
    });
  }
  if (data.review_reasons && data.review_reasons.length > 0) {
    data.review_reasons.forEach(r => {
      reasonsBox.innerHTML += `<div>• <strong>Review:</strong> ${escapeHtml(r)}</div>`;
    });
  }

  // 2. Zero-Loss Accounting Metrics
  const total = data.validation.total_input_records;
  const valid = data.validation.valid_records_count;
  const quarantined = data.validation.quarantined_records_count;
  const rate = data.validation.contract_pass_rate;

  document.getElementById("metric-total").textContent = Number(total).toLocaleString();
  document.getElementById("metric-valid").textContent = Number(valid).toLocaleString();
  document.getElementById("metric-quarantine").textContent = Number(quarantined).toLocaleString();
  document.getElementById("metric-rate").textContent = `${rate}%`;

  document.getElementById("acc-total").textContent = total;
  document.getElementById("acc-valid").textContent = valid;
  document.getElementById("acc-quarantine").textContent = quarantined;

  // 3. Sandbox Verification Test Cases
  const testList = document.getElementById("test-cases-list");
  testList.innerHTML = "";
  const testBadge = document.getElementById("tests-summary-badge");

  if (data.validation.all_tests_passed) {
    testBadge.className = "badge badge-success";
    testBadge.textContent = "All Tests Passed";
  } else {
    testBadge.className = "badge badge-danger";
    testBadge.textContent = "Test Failures Detected";
  }

  (data.validation.test_case_results || []).forEach(tc => {
    const li = document.createElement("li");
    li.className = `test-item ${tc.passed ? "passed" : "failed"}`;
    li.innerHTML = `
      <div>
        <div class="test-name">${tc.passed ? "✓" : "✕"} ${escapeHtml(tc.test_name)}</div>
        <div class="test-desc">Expected: ${escapeHtml(tc.expected_behavior)} | Actual: ${escapeHtml(tc.actual_behavior)}</div>
        ${tc.error_message ? `<div class="alert alert-error" style="margin-top:4px;padding:4px 8px;">${escapeHtml(tc.error_message)}</div>` : ""}
      </div>
      <span class="badge ${tc.passed ? "badge-success" : "badge-danger"}">${tc.passed ? "PASS" : "FAIL"}</span>
    `;
    testList.appendChild(li);
  });

  // 4. Generated Adapter Code
  document.getElementById("adapter-code-view").textContent = data.adapter.python_code;

  // 5. Quarantined Records Table
  const qSection = document.getElementById("quarantine-section");
  const qTbody = document.getElementById("quarantine-tbody");
  const qBadge = document.getElementById("quarantine-count-badge");
  qTbody.innerHTML = "";

  if (quarantined > 0) {
    qSection.classList.remove("hidden");
    qBadge.textContent = `${quarantined} Records Quarantined`;
    qBadge.className = "badge badge-quarantine";

    (data.validation.sample_quarantined_records || []).forEach(qr => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="font-mono">Row #${qr.row_index}</td>
        <td><strong style="color:var(--accent-red-bright);">${escapeHtml(qr.failure_reasons.join("; "))}</strong></td>
        <td><pre class="font-mono" style="font-size:11px;margin:0;max-height:80px;overflow:auto;">${escapeHtml(JSON.stringify(qr.raw_record, null, 2))}</pre></td>
      `;
      qTbody.appendChild(tr);
    });
  } else {
    qBadge.textContent = "0 Records Quarantined";
    qBadge.className = "badge badge-success";
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="3" style="text-align:center;color:var(--text-muted);">No records were quarantined. 100% of rows passed contract validation.</td>`;
    qTbody.appendChild(tr);
  }

  // 6. Download links
  const sessionId = data.session_id;
  document.getElementById("btn-download-md").href = `/api/download/report/${sessionId}?format=md`;
  document.getElementById("btn-download-json").href = `/api/download/report/${sessionId}?format=json`;
  document.getElementById("btn-download-py").href = `/api/download/adapter/${sessionId}`;
  document.getElementById("btn-download-adapter").href = `/api/download/adapter/${sessionId}`;

  // Unhide & Scroll
  document.getElementById("step-results").classList.remove("hidden");
  document.getElementById("step-results").scrollIntoView({ behavior: "smooth" });
}

// -----------------------------------------------------------------------------
// Utilities
// -----------------------------------------------------------------------------
function handleCopyCode() {
  const code = document.getElementById("adapter-code-view").textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.getElementById("btn-copy-code");
    const orig = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = orig; }, 1800);
  });
}

function showError(msg) {
  const alert = document.getElementById("error-alert");
  document.getElementById("error-message").textContent = msg;
  alert.classList.remove("hidden");
  alert.scrollIntoView({ behavior: "smooth" });
}

function hideError() {
  document.getElementById("error-alert").classList.add("hidden");
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
