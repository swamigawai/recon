/**
   RECON — THE INTEGRATION READINESS ENGINE
   World-Class UI/UX Design Strategy & Engineering Specification
   Technical Brutalism meets Swiss Precision Frontend Controller
   Zero Client-Side Logic Creep | Strict Human-in-the-Loop Approval
   ========================================================================== */

// Global State
let currentSessionId = null;
let currentAssessment = null;
let currentResults = null;
let currentStep = 1;
let activeContractTab = "sample";
let activeDrawerTab = "evidence";
let activeMapFilter = "all";
let mappingOverrides = {};
let sampleContractsMap = {};
let sampleDatasetsMap = {};

// Inspector Drawer State (Global Module Scope)
let isDrawerPinned = false;
let drawerHoverTimer = null;
let currentPlaygroundSamples = [];

function updateInspectorUI(isOpen, isPinned) {
  const edgeTab = document.getElementById("inspector-edge-tab");
  const topBtn = document.getElementById("btn-inspector-toggle");
  if (edgeTab) edgeTab.classList.toggle("active", isOpen);
  if (topBtn) {
    topBtn.classList.toggle("active", isPinned || isOpen);
    topBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
  }
}

function openInspectorDrawer(pin = false) {
  clearTimeout(drawerHoverTimer);
  const drawer = document.getElementById("contextual-drawer");
  if (drawer) drawer.classList.remove("collapsed");
  if (pin) isDrawerPinned = true;
  updateInspectorUI(true, isDrawerPinned);
}

function closeInspectorDrawer(force = false) {
  clearTimeout(drawerHoverTimer);
  const drawer = document.getElementById("contextual-drawer");
  if (force || !isDrawerPinned) {
    if (force) isDrawerPinned = false;
    if (drawer) drawer.classList.add("collapsed");
    updateInspectorUI(false, isDrawerPinned);
  }
}

function toggleInspectorDrawerPin() {
  const drawer = document.getElementById("contextual-drawer");
  isDrawerPinned = !isDrawerPinned;
  if (drawer) drawer.classList.toggle("collapsed", !isDrawerPinned);
  updateInspectorUI(isDrawerPinned, isDrawerPinned);
}

// Active row selection for keyboard navigation
let selectedMappingIndex = 0;
let selectedProfileIndex = 0;
let selectedQuarantineIndex = 0;

// Staged files
let stagedSourceFile = null;
let stagedContractFile = null;
let stagedMappingSpecFile = null;

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initShell();
  initGuide();
  initCommandPalette();
  initDynamicIsland();
  initPresetBenchmarks();
  initMappingViewToggle();
  loadSampleDatasets();
  loadSampleContracts();
  bindDropZones();
  bindKeyboardNavigation();
  bindActions();
});

// =============================================================================
// Theme Controller (Cyber Dark Mode Default / High-Tech Developer Tool)
// =============================================================================

function initTheme() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlTheme = urlParams.get("theme");
  const isEmbed = urlParams.get("embed") === "true";

  if (isEmbed) {
    document.body.classList.add("is-embed-mode");
  }

  let savedTheme = urlTheme || localStorage.getItem("recon-theme-v4");
  if (!savedTheme) {
    savedTheme = "dark";
    localStorage.setItem("recon-theme-v4", "dark");
  }
  applyTheme(savedTheme);

  const themeBtn = document.getElementById("btn-theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem("recon-theme-v4", next);
      SoundEngine.playClick();
    });
  }

  const soundBtn = document.getElementById("btn-sound-toggle");
  if (soundBtn) {
    updateSoundButtonUI();
    soundBtn.addEventListener("click", () => {
      SoundEngine.toggleMute();
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const icon = document.getElementById("theme-toggle-icon");
  const text = document.getElementById("theme-toggle-text");
  if (icon && text) {
    if (theme === "dark") {
      icon.innerHTML = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px;"><circle cx="8" cy="8" r="3.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/></svg>`;
      text.textContent = "Light";
    } else {
      icon.innerHTML = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px;"><path d="M13.5 9.5a6 6 0 1 1-7-7 5 5 0 0 0 7 7z"/></svg>`;
      text.textContent = "Dark";
    }
  }
}

// =============================================================================
// Interactive Guide & Spotlight Tour Controller
// =============================================================================

const GUIDE_STEPS = [
  {
    step: 1,
    num: "01",
    name: "01 Dual-Port Ingest Cockpit",
    badge: "Port 1 & Port 2",
    screenId: "screen-ingest",
    targetSelector: ".dual-port-container",
    stepperNavId: "step-nav-1",
    shortDesc: "Stage raw source records (CSV/JSON) on Port 1 and target contract on Port 2.",
    desc: "Recon's workflow starts by staging raw incoming records on the left (Port 1) and your target destination schema on the right (Port 2). Recon validates structure and headers before transforming any data.",
    cards: [
      {
        tag: "PORT 1: SOURCE DATASET",
        desc: "Upload CSV, TSV, JSON, JSONL payloads up to 100MB or select a preloaded sample."
      },
      {
        tag: "PORT 2: TARGET CONTRACT",
        desc: "Ingest strict JSON Schema (Draft-07/2020-12), OpenAPI 3.0/3.1, or preloaded target schemas."
      },
      {
        tag: "PRE-FLIGHT VALIDATION",
        desc: "Instant client-side verification confirms payload presence, non-empty records, and syntax validity."
      }
    ]
  },
  {
    step: 2,
    num: "02",
    name: "02 Source Dataset Profile Matrix",
    badge: "Data Profiling",
    screenId: "screen-profile",
    targetSelector: "#screen-profile .table-container",
    stepperNavId: "step-nav-2",
    shortDesc: "Inspect inferred types, 44px nullity micro-bars, and quality anomalies per column.",
    desc: "Recon inspects every column of the source dataset deterministically without guessing. It evaluates cardinality, null ratios, sample values, and flags dirty data like trailing whitespace or currency strings in numbers.",
    cards: [
      {
        tag: "INFERRED DATA TYPES",
        desc: "Identifies strings, integers, floats, timestamps, or booleans with rigorous type inference rules."
      },
      {
        tag: "44PX NULLITY MICRO-BARS",
        desc: "Instant visual mini-bars per column: green indicates filled values, amber/red indicates missing nulls."
      },
      {
        tag: "QUALITY FORENSICS",
        desc: "Highlights dirty data patterns like trailing whitespace, mixed formats, or currency strings."
      }
    ]
  },
  {
    step: 3,
    num: "03",
    name: "03 Mapping Review Studio",
    badge: "Heuristic Alignment",
    screenId: "screen-map",
    targetSelector: "#screen-map .table-container",
    stepperNavId: "step-nav-3",
    shortDesc: "Audit field mappings across 6 visual states. Missing required fields are flagged in red.",
    desc: "Recon proposes mappings based on evidence, naming similarity, and semantic type compatibility. It adheres to a strict fail-closed policy: unmapped required fields are hard blockers that must be resolved by a human.",
    cards: [
      {
        tag: "6 VISUAL STATES",
        desc: "Approved (Green), Proposed (Indigo), Ambiguous (Amber), Missing Required (Red), Unresolved, and Type Cast."
      },
      {
        tag: "MISSING REQUIRED ALERTS",
        desc: "Unmapped required target fields glow in soft red with explicit [MISSING REQUIRED FIELD] dropdown alerts."
      },
      {
        tag: "CONTEXTUAL INSPECTOR",
        desc: "Click any row to open the 4-tab right drawer: Engine Evidence, Sample Values, Transform AST, and Meta."
      }
    ]
  },
  {
    step: 4,
    num: "04",
    name: "04 Risk Radar & Approval Gate",
    badge: "Mandatory Gate",
    screenId: "screen-audit",
    targetSelector: "#screen-audit .recon-card",
    stepperNavId: "step-nav-4",
    shortDesc: "Mandatory human sign-off boundary. Hard blockers prevent adapter compilation until resolved.",
    desc: "A formal pre-flight audit prevents breaking integrations before they are compiled. If any required field is missing or ambiguous, Recon locks adapter generation and provides remediation instructions.",
    cards: [
      {
        tag: "CRITICAL BLOCKERS",
        desc: "Adapter synthesis is locked until all required target fields have verified source mappings."
      },
      {
        tag: "REMEDIATION ACTIONS",
        desc: "Every detected risk card provides direct, actionable advice on which screen and column to fix."
      },
      {
        tag: "EXPLICIT ACKNOWLEDGMENT",
        desc: "Requires human-in-the-loop developer check-off before synthesizing adapter code."
      }
    ]
  },
  {
    step: 5,
    num: "05",
    name: "05 Adapter Code Workbench",
    badge: "Code Synthesis",
    screenId: "screen-adapter",
    targetSelector: "#screen-adapter .code-workbench",
    stepperNavId: "step-nav-5",
    shortDesc: "Inspect synthesized, production-ready Python adapter code compiled from the mapping AST.",
    desc: "Recon compiles the human-approved mapping decisions into a standalone Python 3.11 adapter. The adapter handles type casting, regex pattern validation, and invalid-record quarantine safely in local sandbox memory.",
    cards: [
      {
        tag: "STANDALONE PYTHON CODE",
        desc: "Production-ready transformation functions synthesized directly from the approved mapping plan."
      },
      {
        tag: "SAFE LOCAL SANDBOX",
        desc: "Executed in an isolated in-process memory sandbox with no remote calls or external egress."
      },
      {
        tag: "INSTANT CODE EXPORT",
        desc: "Copy or download the clean adapter script (.py) for direct inclusion into your ETL or microservice."
      }
    ]
  },
  {
    step: 6,
    num: "06",
    name: "06 Validation Lab & Quarantine Ledger",
    badge: "Zero Data Loss",
    screenId: "screen-validate",
    targetSelector: "#screen-validate .metrics-grid",
    stepperNavId: "step-nav-6",
    shortDesc: "Verify zero data loss accounting: Total Input = Valid Output + Quarantined Records.",
    desc: "The engine transforms every row through the synthesized adapter. Recon's fundamental invariant is verified: every record must either pass cleanly or be quarantined with full forensic diagnostic reasons.",
    cards: [
      {
        tag: "LEDGER ACCOUNTING IDENTITY",
        desc: "Verified zero-loss equation: N_total = N_valid + N_quarantine. No record is ever silently lost."
      },
      {
        tag: "SYNTHETIC TEST SUITE",
        desc: "Executes 4 automated unit tests testing valid transforms, malformed dates, and missing keys."
      },
      {
        tag: "QUARANTINE FORENSICS",
        desc: "Quarantined records are preserved with original payloads and specific contract failure reasons."
      }
    ]
  },
  {
    step: 7,
    num: "07",
    name: "07 Readiness Dossier & Certified Artifacts",
    badge: "Certified Deliverables",
    screenId: "screen-dossier",
    targetSelector: "#screen-dossier .dossier-card-grid",
    stepperNavId: "step-nav-7",
    shortDesc: "Download complete integration deliverables, audit report, and reusable mapping spec.",
    desc: "Recon outputs the final integration package: the certified Python adapter script, Markdown & JSON readiness reports, transformed valid records, quarantined diagnostics, and a reusable mapping specification.",
    cards: [
      {
        tag: "READINESS VERDICT",
        desc: "Formal integration certification score: READY (100% yield) or BLOCKED with exact error counts."
      },
      {
        tag: "REUSABLE MAPPING SPEC",
        desc: "Exports versioned mapping specification (.json) with SHA-256 fingerprint for automated CI/CD gates."
      },
      {
        tag: "EPHEMERAL PURGE",
        desc: "One-click memory purge guarantees ephemeral session privacy and cleans all temporary state."
      }
    ]
  }
];

let currentGuideStepIndex = 0;
let isSpotlightTourActive = false;

function initGuide() {
  const btnGuide = document.getElementById("btn-guide");
  const btnGuideBar = document.getElementById("btn-guide-bar");
  const btnCloseGuide = document.getElementById("btn-close-guide");
  const btnPrev = document.getElementById("btn-guide-prev");
  const btnNext = document.getElementById("btn-guide-next");
  const btnSpotlightToggle = document.getElementById("btn-guide-spotlight-toggle");

  if (btnGuide) btnGuide.addEventListener("click", () => openGuide(currentGuideStepIndex));
  if (btnGuideBar) btnGuideBar.addEventListener("click", () => openGuide(currentGuideStepIndex));
  if (btnCloseGuide) btnCloseGuide.addEventListener("click", closeGuide);

  if (btnPrev) btnPrev.addEventListener("click", () => navigateGuideStep(-1));
  if (btnNext) btnNext.addEventListener("click", () => navigateGuideStep(1));

  if (btnSpotlightToggle) {
    btnSpotlightToggle.addEventListener("click", () => {
      startSpotlightTour(currentGuideStepIndex);
    });
  }

  // Guide step tab clicks
  const stepBtns = document.querySelectorAll("#guide-stepper-tabs button");
  stepBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-gstep"), 10) - 1;
      setGuideStep(idx);
    });
  });

  // Guide dots clicks
  const dots = document.querySelectorAll("#guide-dots-container .recon-guide-dot");
  dots.forEach(dot => {
    dot.addEventListener("click", () => {
      const idx = parseInt(dot.getAttribute("data-gstep"), 10) - 1;
      setGuideStep(idx);
    });
  });

  // Quick Demo action inside Guide
  const btnGuideDemo = document.getElementById("btn-guide-quick-demo");
  if (btnGuideDemo) {
    btnGuideDemo.addEventListener("click", () => {
      closeGuide();
      closeTour();
      handleQuickDemoLoad();
    });
  }

  // Floating Tour Card controls
  const btnTourExpand = document.getElementById("btn-tour-expand");
  const btnTourClose = document.getElementById("btn-tour-close");
  const btnTourPrev = document.getElementById("btn-tour-prev");
  const btnTourNext = document.getElementById("btn-tour-next");

  if (btnTourExpand) {
    btnTourExpand.addEventListener("click", () => {
      closeTour();
      openGuide(currentGuideStepIndex);
    });
  }
  if (btnTourClose) btnTourClose.addEventListener("click", closeTour);
  if (btnTourPrev) btnTourPrev.addEventListener("click", () => stepFloatingTour(-1));
  if (btnTourNext) btnTourNext.addEventListener("click", () => stepFloatingTour(1));
}

function openGuide(stepIndex = 0) {
  clearSpotlights();
  closeTour();
  currentGuideStepIndex = Math.max(0, Math.min(stepIndex, GUIDE_STEPS.length - 1));
  document.getElementById("modal-guide").classList.remove("hidden");
  renderGuideStep(currentGuideStepIndex);
}

function closeGuide() {
  document.getElementById("modal-guide").classList.add("hidden");
}

function toggleGuideModal() {
  const modal = document.getElementById("modal-guide");
  if (modal.classList.contains("hidden")) {
    openGuide(currentStep - 1);
  } else {
    closeGuide();
  }
}

function setGuideStep(idx) {
  currentGuideStepIndex = Math.max(0, Math.min(idx, GUIDE_STEPS.length - 1));
  renderGuideStep(currentGuideStepIndex);
}

function navigateGuideStep(delta) {
  const nextIdx = currentGuideStepIndex + delta;
  if (nextIdx >= 0 && nextIdx < GUIDE_STEPS.length) {
    setGuideStep(nextIdx);
  }
}

function renderGuideStep(idx) {
  const data = GUIDE_STEPS[idx];
  if (!data) return;

  // Update tabs
  const tabBtns = document.querySelectorAll("#guide-stepper-tabs button");
  tabBtns.forEach((b, i) => b.classList.toggle("active", i === idx));

  // Update dots
  const dots = document.querySelectorAll("#guide-dots-container .recon-guide-dot");
  dots.forEach((d, i) => d.classList.toggle("active", i === idx));

  // Update text
  document.getElementById("guide-step-name").textContent = data.name;
  document.getElementById("guide-step-badge").textContent = data.badge;
  document.getElementById("guide-step-desc").textContent = data.desc;

  // Render cards
  const grid = document.getElementById("guide-cards-grid");
  grid.innerHTML = data.cards.map(c => `
    <div class="recon-guide-card">
      <span class="recon-guide-card-tag">${escapeHtml(c.tag)}</span>
      <span class="recon-guide-card-desc">${escapeHtml(c.desc)}</span>
    </div>
  `).join("");

  // Prev / Next button state
  const btnPrev = document.getElementById("btn-guide-prev");
  const btnNext = document.getElementById("btn-guide-next");
  if (btnPrev) btnPrev.disabled = (idx === 0);
  if (btnNext) {
    if (idx === GUIDE_STEPS.length - 1) {
      btnNext.textContent = "Finish Guide";
      btnNext.onclick = closeGuide;
    } else {
      btnNext.textContent = "Next Step →";
      btnNext.onclick = () => navigateGuideStep(1);
    }
  }

  // Quick Demo hint visibility
  const actionBox = document.getElementById("guide-step-action-box");
  if (actionBox) {
    actionBox.classList.toggle("hidden", idx > 2 && currentAssessment !== null);
  }
}

function startSpotlightTour(idx = 0) {
  closeGuide();
  isSpotlightTourActive = true;
  currentGuideStepIndex = Math.max(0, Math.min(idx, GUIDE_STEPS.length - 1));
  applySpotlightToStep(currentGuideStepIndex);
}

function applySpotlightToStep(idx) {
  clearSpotlights();
  const data = GUIDE_STEPS[idx];
  if (!data) return;

  // Update floating widget
  const card = document.getElementById("recon-guide-floating-card");
  card.classList.remove("hidden");
  document.getElementById("tour-floating-step-label").textContent = data.name;
  document.getElementById("tour-floating-desc").textContent = data.shortDesc;
  document.getElementById("tour-floating-counter").textContent = `Step ${idx + 1} of ${GUIDE_STEPS.length}`;

  const btnPrev = document.getElementById("btn-tour-prev");
  const btnNext = document.getElementById("btn-tour-next");
  if (btnPrev) btnPrev.disabled = (idx === 0);
  if (btnNext) {
    btnNext.textContent = (idx === GUIDE_STEPS.length - 1) ? "Done" : "Next →";
  }

  // If the target screen is already unlocked and not active, navigate to it
  if (isStepAvailable(data.step) && currentStep !== data.step) {
    navigateToStep(data.step);
  }

  // Find target element to spotlight
  let targetEl = null;
  if (currentStep === data.step) {
    targetEl = document.querySelector(data.targetSelector);
  }
  // If target screen is not unlocked or not visible, spotlight the stepper tab
  if (!targetEl) {
    targetEl = document.getElementById(data.stepperNavId);
  }

  if (targetEl) {
    targetEl.classList.add("recon-tour-spotlight");
    targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function stepFloatingTour(delta) {
  const nextIdx = currentGuideStepIndex + delta;
  if (nextIdx >= 0 && nextIdx < GUIDE_STEPS.length) {
    currentGuideStepIndex = nextIdx;
    applySpotlightToStep(currentGuideStepIndex);
  } else if (nextIdx >= GUIDE_STEPS.length) {
    closeTour();
  }
}

function clearSpotlights() {
  document.querySelectorAll(".recon-tour-spotlight").forEach(el => {
    el.classList.remove("recon-tour-spotlight");
  });
}

function closeTour() {
  clearSpotlights();
  isSpotlightTourActive = false;
  const card = document.getElementById("recon-guide-floating-card");
  if (card) card.classList.add("hidden");
}

// =============================================================================
// Shell & Stepper Navigation
// =============================================================================

function initShell() {
  initCrtEngine();
  const steps = document.querySelectorAll(".recon-step-item");
  steps.forEach(step => {
    step.addEventListener("click", () => {
      const targetStep = parseInt(step.getAttribute("data-step"), 10);
      if (isStepAvailable(targetStep)) {
        navigateToStep(targetStep);
      } else {
        triggerHapticFeedback(step);
        if (!currentAssessment) {
          showGlobalError(
            "WORKFLOW GATED",
            "Screen 02 (PROFILE) and 03 (MAP) unlock after inspection. Stage a dataset & contract in Screen 01, then click 'INITIALIZE RECON INSPECTION →' (or click Quick Load Sample Fixtures).",
            step
          );
        } else if (!currentResults && targetStep >= 5) {
          showGlobalError(
            "APPROVAL REQUIRED",
            "Screen 05 (ADAPTER) and 06 (VALIDATE) unlock after reviewing the Risk Radar in 04 AUDIT and clicking 'APPROVE & COMPILE ADAPTER →'.",
            step
          );
        }
      }
    });
  });

  const btnQuickDemo = document.getElementById("btn-quick-demo");
  if (btnQuickDemo) {
    btnQuickDemo.addEventListener("click", handleQuickDemoLoad);
  }

  const btnQuickIndian = document.getElementById("btn-quick-indian-voicemail");
  if (btnQuickIndian) {
    btnQuickIndian.addEventListener("click", () => loadScenario("indian_voicemail"));
  }

  const btnQuickNyc = document.getElementById("btn-quick-nyc311");
  if (btnQuickNyc) {
    btnQuickNyc.addEventListener("click", () => loadScenario("nyc311"));
  }

  // Drawer tabs
  const drawerTabs = document.querySelectorAll(".recon-drawer-tab-btn");
  drawerTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      drawerTabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeDrawerTab = btn.getAttribute("data-dtab");
      switchDrawerTab(activeDrawerTab);
    });
  });

  // Contract tabs in Screen A
  const ctabBtns = document.querySelectorAll("[data-ctab]");
  ctabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      ctabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeContractTab = btn.getAttribute("data-ctab");
      document.getElementById("ctab-content-sample").classList.toggle("hidden", activeContractTab !== "sample");
      document.getElementById("ctab-content-upload").classList.toggle("hidden", activeContractTab !== "upload");
      document.getElementById("ctab-content-paste").classList.toggle("hidden", activeContractTab !== "paste");
      updatePreflightStatus();
    });
  });

  // Mapping filter tabs in Screen C
  const mapFilterBtns = document.querySelectorAll("[data-mapfilter]");
  mapFilterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      mapFilterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeMapFilter = btn.getAttribute("data-mapfilter");
      filterMappingsTable();
    });
  });

  // Drawer close & toggle buttons + Side-of-Screen Hover Pop-Out
  const edgeTab = document.getElementById("inspector-edge-tab");
  const drawer = document.getElementById("contextual-drawer");

  if (edgeTab && drawer) {
    // Hovering search logo tab pops out the drawer
    edgeTab.addEventListener("mouseenter", () => {
      openInspectorDrawer(false);
    });

    edgeTab.addEventListener("mouseleave", () => {
      if (!isDrawerPinned) {
        drawerHoverTimer = setTimeout(() => {
          closeInspectorDrawer(false);
        }, 320);
      }
    });

    // Clicking the tab pins/unpins open
    edgeTab.addEventListener("click", () => {
      toggleInspectorDrawerPin();
    });

    // Mouse inside drawer keeps it open
    drawer.addEventListener("mouseenter", () => {
      clearTimeout(drawerHoverTimer);
      if (edgeTab) edgeTab.classList.add("active");
    });

    // Mouse leaving drawer slides it back into the edge if not pinned
    drawer.addEventListener("mouseleave", () => {
      if (!isDrawerPinned) {
        drawerHoverTimer = setTimeout(() => {
          closeInspectorDrawer(false);
        }, 320);
      }
    });

    const btnCloseDrawer = document.getElementById("btn-close-drawer");
    if (btnCloseDrawer) {
      btnCloseDrawer.addEventListener("click", () => {
        closeInspectorDrawer(true);
      });
    }
  }

  const btnToggleInspector = document.getElementById("btn-toggle-inspector");
  if (btnToggleInspector && drawer) {
    btnToggleInspector.addEventListener("click", () => {
      toggleInspectorDrawerPin();
    });
  }

  const btnInspectorToggle = document.getElementById("btn-inspector-toggle");
  if (btnInspectorToggle && drawer) {
    btnInspectorToggle.addEventListener("click", () => {
      toggleInspectorDrawerPin();
    });
  }

  // Shortcuts modal
  const btnShortcuts = document.getElementById("btn-shortcuts");
  if (btnShortcuts) btnShortcuts.addEventListener("click", toggleShortcutsModal);
  const btnShortcutsBar = document.getElementById("btn-shortcuts-bar");
  if (btnShortcutsBar) btnShortcutsBar.addEventListener("click", toggleShortcutsModal);
  const btnCloseShortcuts = document.getElementById("btn-close-shortcuts");
  if (btnCloseShortcuts) btnCloseShortcuts.addEventListener("click", toggleShortcutsModal);

  // Reset modal
  document.getElementById("btn-reset-session").addEventListener("click", () => {
    document.getElementById("modal-reset-session").classList.remove("hidden");
  });
  document.getElementById("btn-cancel-reset").addEventListener("click", () => {
    document.getElementById("modal-reset-session").classList.add("hidden");
  });
  document.getElementById("btn-confirm-reset").addEventListener("click", handlePurgeSession);
  document.getElementById("btn-purge-session").addEventListener("click", handlePurgeSession);

  // Global error bar close
  document.getElementById("btn-close-error").addEventListener("click", hideGlobalError);

  // Initialize Preflight Quick Peek
  initPreflightPeek();

  // Initialize Transform Expression Playground
  initTransformPlayground();
}

function isStepAvailable(targetStep) {
  if (targetStep === 1) return true;
  if (targetStep >= 2 && targetStep <= 4) return Boolean(currentAssessment);
  if (targetStep >= 5 && targetStep <= 7) return Boolean(currentResults);
  return false;
}

function navigateToStep(stepNumber) {
  if (!isStepAvailable(stepNumber)) return;
  currentStep = stepNumber;
  SoundEngine.playClick();

  // If navigating to certified dossier with passing state, fire confetti & celebration
  if (stepNumber === 7 && currentResults && String(currentResults.readiness_state).toLowerCase() === "pass") {
    setTimeout(() => {
      triggerConfettiCelebration();
      SoundEngine.playCelebration();
    }, 180);
  }

  // Update stepper UI
  for (let s = 1; s <= 7; s++) {
    const navItem = document.getElementById(`step-nav-${s}`);
    navItem.classList.remove("active", "completed", "available");

    const available = isStepAvailable(s);
    if (available && s !== currentStep) {
      navItem.classList.add("available");
    }

    if (s < currentStep) {
      navItem.classList.add("completed");
      navItem.querySelector(".recon-step-num").innerHTML = '<span class="recon-step-check">✓</span>';
    } else if (s === currentStep) {
      navItem.classList.add("active");
      navItem.querySelector(".recon-step-num").textContent = s < 10 ? `0${s}` : `${s}`;
    } else {
      navItem.querySelector(".recon-step-num").textContent = s < 10 ? `0${s}` : `${s}`;
    }
  }

  // Switch screen visibility
  const screens = [
    "screen-ingest",
    "screen-profile",
    "screen-map",
    "screen-audit",
    "screen-adapter",
    "screen-validate",
    "screen-dossier"
  ];

  screens.forEach((id, idx) => {
    const el = document.getElementById(id);
    if (el) {
      el.classList.toggle("hidden", idx + 1 !== currentStep);
    }
  });

  // Smooth scroll to top of canvas
  document.getElementById("workspace-canvas").scrollTo({ top: 0, behavior: "smooth" });

  // Collapse drawer when navigating to non-inspection screens (01, 04, 05, 06, 07)
  // to ensure 100% full canvas width and maximum breathing room
  if ([1, 4, 5, 6, 7].includes(stepNumber)) {
    document.getElementById("contextual-drawer").classList.add("collapsed");
  }

  // When opening step 03, trigger flow graph path recalculation
  if (stepNumber === 3 && activeMappingView === "flow") {
    requestAnimationFrame(() => {
      updateFlowConnections();
    });
  }

  // Update Dynamic Health Island for current step
  updateDynamicIsland();
}

function switchDrawerTab(tabName) {
  document.getElementById("dtab-pane-evidence").classList.toggle("hidden", tabName !== "evidence");
  document.getElementById("dtab-pane-samples").classList.toggle("hidden", tabName !== "samples");
  document.getElementById("dtab-pane-ast").classList.toggle("hidden", tabName !== "ast");
  document.getElementById("dtab-pane-meta").classList.toggle("hidden", tabName !== "meta");
}

function toggleShortcutsModal() {
  const modal = document.getElementById("modal-shortcuts");
  modal.classList.toggle("hidden");
}

// =============================================================================
// Web Audio Synthesizer Engine (Zero-Latency UI Micro-Acoustics)
// =============================================================================

let audioCtx = null;
let isAudioMuted = localStorage.getItem("recon_audio_muted") === "true";

function getAudioContext() {
  if (isAudioMuted) return null;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return null;
    if (!audioCtx) {
      audioCtx = new AudioContextClass();
    }
    if (audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    return audioCtx;
  } catch (_) {
    return null;
  }
}

const SoundEngine = {
  isMuted: () => isAudioMuted,

  toggleMute: () => {
    isAudioMuted = !isAudioMuted;
    localStorage.setItem("recon_audio_muted", isAudioMuted ? "true" : "false");
    updateSoundButtonUI();
    if (!isAudioMuted) {
      SoundEngine.playClick();
    }
    return isAudioMuted;
  },

  playClick: () => {
    const ctx = getAudioContext();
    if (!ctx) return;
    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const now = ctx.currentTime;
      osc.type = "sine";
      osc.frequency.setValueAtTime(600, now);
      osc.frequency.exponentialRampToValueAtTime(320, now + 0.035);
      gain.gain.setValueAtTime(0.04, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.035);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.04);
    } catch (_) {}
  },

  playError: () => {
    const ctx = getAudioContext();
    if (!ctx) return;
    try {
      const now = ctx.currentTime;
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.type = "triangle";
      osc1.frequency.setValueAtTime(140, now);
      osc1.frequency.exponentialRampToValueAtTime(55, now + 0.16);

      osc2.type = "sine";
      osc2.frequency.setValueAtTime(95, now);
      osc2.frequency.exponentialRampToValueAtTime(40, now + 0.16);

      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.16);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.18);
      osc2.stop(now + 0.18);
    } catch (_) {}
  },

  playSuccess: () => {
    const ctx = getAudioContext();
    if (!ctx) return;
    try {
      const now = ctx.currentTime;
      const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const startTime = now + idx * 0.06;
        const dur = 0.22;
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, startTime);
        gain.gain.setValueAtTime(0.045, startTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, startTime + dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + dur);
      });
    } catch (_) {}
  },

  playCelebration: () => {
    const ctx = getAudioContext();
    if (!ctx) return;
    try {
      const now = ctx.currentTime;
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const startTime = now + idx * 0.08;
        const dur = 0.38;
        osc.type = idx === 3 ? "triangle" : "sine";
        osc.frequency.setValueAtTime(freq, startTime);
        gain.gain.setValueAtTime(0.06, startTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, startTime + dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + dur);
      });
    } catch (_) {}
  }
};

function updateSoundButtonUI() {
  const btn = document.getElementById("btn-sound-toggle");
  const icon = document.getElementById("sound-toggle-icon");
  const text = document.getElementById("sound-toggle-text");
  if (!btn) return;
  btn.classList.toggle("is-muted", isAudioMuted);
  if (isAudioMuted) {
    if (text) text.textContent = "Muted";
    if (icon) {
      icon.innerHTML = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px;"><polygon points="2,5 5,5 9,2 9,14 5,11 2,11" fill="currentColor"/><line x1="12" y1="6" x2="15" y2="10"/><line x1="15" y1="6" x2="12" y2="10"/></svg>`;
    }
  } else {
    if (text) text.textContent = "Sound";
    if (icon) {
      icon.innerHTML = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px;"><polygon points="2,5 5,5 9,2 9,14 5,11 2,11" fill="currentColor"/><path d="M11.5 5.5 C13 7 13 9 11.5 10.5"/></svg>`;
    }
  }
}

// =============================================================================
// Confetti & Particle Celebration Engine (Screen 07 Dossier)
// =============================================================================

let confettiAnimId = null;

function triggerConfettiCelebration() {
  const canvas = document.getElementById("recon-confetti-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  if (confettiAnimId) {
    cancelAnimationFrame(confettiAnimId);
  }

  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.classList.remove("hidden");

  const colors = ["#10B981", "#3B82F6", "#6366F1", "#F59E0B", "#EC4899", "#14B8A6"];
  const particles = [];
  const count = 75;

  for (let i = 0; i < count; i++) {
    particles.push({
      x: canvas.width * 0.5 + (Math.random() - 0.5) * 160,
      y: canvas.height * 0.45 + (Math.random() - 0.5) * 80,
      vx: (Math.random() - 0.5) * 14,
      vy: -(Math.random() * 8 + 6),
      size: Math.random() * 6 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      vRot: (Math.random() - 0.5) * 10,
      alpha: 1,
      gravity: 0.32,
      drag: 0.985,
    });
  }

  let startTime = performance.now();

  function animate(now) {
    const elapsed = (now - startTime) / 1000;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let activeCount = 0;
    particles.forEach(p => {
      p.vx *= p.drag;
      p.vy += p.gravity;
      p.x += p.vx;
      p.y += p.vy;
      p.rotation += p.vRot;

      if (elapsed > 1.4) {
        p.alpha = Math.max(0, p.alpha - 0.025);
      }

      if (p.alpha > 0.01 && p.y < canvas.height + 40) {
        activeCount++;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.globalAlpha = p.alpha;
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size * 0.5, -p.size * 0.5, p.size, p.size * 0.6);
        ctx.restore();
      }
    });

    if (activeCount > 0 && elapsed < 3.2) {
      confettiAnimId = requestAnimationFrame(animate);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvas.classList.add("hidden");
      confettiAnimId = null;
    }
  }

  confettiAnimId = requestAnimationFrame(animate);
}

// =============================================================================
// Haptic Feedback Engine (Physical Vibration & Micro-Jitter Visuals)
// =============================================================================

function triggerHapticFeedback(element = null, pattern = [45, 35, 55]) {
  // 0. Audio synthesizer low resonant error thud
  SoundEngine.playError();

  // 1. Hardware physical vibration via Web Vibration API
  try {
    if (typeof navigator !== "undefined" && "vibrate" in navigator && typeof navigator.vibrate === "function") {
      navigator.vibrate(pattern);
    }
  } catch (_) {
    // Gracefully ignore sandbox/permission limitations
  }

  // 2. Visual micro-haptic jitter/shake
  const target = element || document.getElementById("global-error-bar") || document.getElementById("workspace-canvas");
  if (target && target instanceof Element) {
    target.classList.remove("haptic-vibrate", "haptic-shockwave");
    // Trigger reflow to restart animation reliably
    void target.offsetWidth;
    target.classList.add("haptic-vibrate", "haptic-shockwave");
    setTimeout(() => {
      if (target) {
        target.classList.remove("haptic-vibrate", "haptic-shockwave");
      }
    }, 450);
  }
}

function showGlobalError(title, msg, targetEl = null) {
  const bar = document.getElementById("global-error-bar");
  if (bar) {
    const titleEl = document.getElementById("global-error-title");
    const msgEl = document.getElementById("global-error-msg");
    if (titleEl) titleEl.textContent = title ? `[${title}]` : "[ERROR]";
    if (msgEl) msgEl.textContent = msg;
    bar.classList.remove("hidden");
    triggerHapticFeedback(bar);
  }
  if (targetEl && targetEl !== bar) {
    triggerHapticFeedback(targetEl);
  }
}

function hideGlobalError() {
  document.getElementById("global-error-bar").classList.add("hidden");
}

// =============================================================================
// API Catalogs & Pre-flight Ingestion
// =============================================================================

async function loadSampleDatasets() {
  try {
    const res = await fetch("/api/sample-datasets");
    if (!res.ok) return;
    const datasets = await res.json();
    const select = document.getElementById("sample-dataset-select");
    datasets.forEach(ds => {
      sampleDatasetsMap[ds.id] = ds;
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
      updatePreflightStatus();
    });
  } catch (err) {
    console.error("Failed to load sample contracts:", err);
  }
}

function initPresetBenchmarks() {
  const cards = document.querySelectorAll(".preset-card");
  cards.forEach(card => {
    card.addEventListener("click", () => {
      const scenario = card.getAttribute("data-scenario");
      if (scenario) loadScenario(scenario);
    });
    const btn = card.querySelector(".preset-load-btn");
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const scenario = btn.getAttribute("data-scenario");
        if (scenario) loadScenario(scenario);
      });
    }
  });
}

function loadScenario(scenarioKey) {
  hideGlobalError();
  const dsSelect = document.getElementById("sample-dataset-select");
  const cSelect = document.getElementById("sample-contract-select");

  // Highlight active preset card
  document.querySelectorAll(".preset-card").forEach(c => {
    c.classList.toggle("active-preset", c.getAttribute("data-scenario") === scenarioKey);
  });

  // Switch to preloaded sample contract tab
  const sampleCtabBtn = document.getElementById("ctab-btn-sample");
  if (sampleCtabBtn) sampleCtabBtn.click();

  const scenarioMap = {
    b2b: {
      dsPatterns: ["gate09", "b2b_vendor_invoices", "b2b"],
      contractPatterns: ["gate09", "b2b_vendor_invoice", "b2b"]
    },
    ecommerce: {
      dsPatterns: ["olist_orders", "ecommerce"],
      contractPatterns: ["ecommerce_order", "ecommerce"]
    },
    freight: {
      dsPatterns: ["freight_manifest", "freight"],
      contractPatterns: ["freight_manifest", "dispatch"]
    },
    nyc311: {
      dsPatterns: ["synthetic_nyc_311", "nyc_311", "311"],
      contractPatterns: ["service_request"]
    },
    indian_voicemail: {
      dsPatterns: ["indian_ai_voicemail", "indian"],
      contractPatterns: ["indian_ai_voicemail", "indian"]
    }
  };

  const target = scenarioMap[scenarioKey] || scenarioMap["b2b"];

  if (dsSelect && dsSelect.options.length > 1) {
    let pickedDs = 1;
    for (let i = 1; i < dsSelect.options.length; i++) {
      const val = dsSelect.options[i].value.toLowerCase();
      if (target.dsPatterns.some(p => val.includes(p))) {
        pickedDs = i;
        break;
      }
    }
    dsSelect.selectedIndex = pickedDs;
    dsSelect.dispatchEvent(new Event("change"));
  }

  if (cSelect && cSelect.options.length > 1) {
    let pickedC = 1;
    for (let i = 1; i < cSelect.options.length; i++) {
      const val = cSelect.options[i].value.toLowerCase();
      if (target.contractPatterns.some(p => val.includes(p))) {
        pickedC = i;
        break;
      }
    }
    cSelect.selectedIndex = pickedC;
    cSelect.dispatchEvent(new Event("change"));
  }

  updatePreflightStatus();
}

function handleQuickDemoLoad() {
  loadScenario("b2b");
}

function bindDropZones() {
  // Source dropzone
  const sourceDz = document.getElementById("source-dropzone");
  const sourceInput = document.getElementById("source-file-input");
  const sampleDatasetSelect = document.getElementById("sample-dataset-select");

  sourceDz.addEventListener("click", () => sourceInput.click());
  sourceDz.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      sourceInput.click();
    }
  });
  sourceDz.addEventListener("dragover", e => { e.preventDefault(); sourceDz.classList.add("dragover"); });
  sourceDz.addEventListener("dragleave", () => sourceDz.classList.remove("dragover"));
  sourceDz.addEventListener("drop", e => {
    e.preventDefault();
    sourceDz.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleSourceFileStaged(e.dataTransfer.files[0]);
    }
  });
  sourceInput.addEventListener("change", () => {
    if (sourceInput.files.length > 0) {
      handleSourceFileStaged(sourceInput.files[0]);
    }
  });
  sampleDatasetSelect.addEventListener("change", () => {
    if (sampleDatasetSelect.value) {
      stagedSourceFile = null;
      sourceInput.value = "";
      const ds = sampleDatasetsMap[sampleDatasetSelect.value];
      document.getElementById("source-status-text").textContent = `Preloaded: ${ds.file_name}`;
      document.getElementById("source-status-meta").textContent = `Format: ${ds.format.toUpperCase()} | Ready`;
      document.getElementById("source-format-pill").textContent = ds.format.toUpperCase();
      updatePreflightStatus();
    }
  });

  // Contract dropzone
  const contractDz = document.getElementById("contract-dropzone");
  const contractInput = document.getElementById("contract-file-input");
  const contractTextArea = document.getElementById("contract-text-area");

  contractDz.addEventListener("click", () => contractInput.click());
  contractDz.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      contractInput.click();
    }
  });
  contractDz.addEventListener("dragover", e => { e.preventDefault(); contractDz.classList.add("dragover"); });
  contractDz.addEventListener("dragleave", () => contractDz.classList.remove("dragover"));
  contractDz.addEventListener("drop", e => {
    e.preventDefault();
    contractDz.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleContractFileStaged(e.dataTransfer.files[0]);
    }
  });
  contractInput.addEventListener("change", () => {
    if (contractInput.files.length > 0) {
      handleContractFileStaged(contractInput.files[0]);
    }
  });

  contractTextArea.addEventListener("input", () => {
    const text = contractTextArea.value.trim();
    const syntaxErr = document.getElementById("contract-json-syntax-error");
    if (!text) {
      syntaxErr.classList.add("hidden");
      syntaxErr.textContent = "";
      updatePreflightStatus();
      return;
    }
    try {
      const parsed = JSON.parse(text);
      syntaxErr.classList.add("hidden");
      document.getElementById("contract-status-text").textContent = `Pasted Contract: ${parsed.contract_name || "Custom"}`;
      document.getElementById("contract-status-meta").textContent = `Fields: ${Object.keys(parsed.fields || {}).length}`;
    } catch (err) {
      syntaxErr.classList.remove("hidden");
      syntaxErr.textContent = `JSON Syntax Error: ${err.message}`;
      document.getElementById("contract-status-text").textContent = "Invalid JSON Contract";
      document.getElementById("contract-status-meta").textContent = "Syntax Error";
      triggerHapticFeedback(contractTextArea);
    }
    updatePreflightStatus();
  });
}

function handleSourceFileStaged(file) {
  if (!file || file.size === 0) {
    const dz = document.getElementById("source-dropzone");
    triggerHapticFeedback(dz);
    showGlobalError("EMPTY FILE", "The selected source file is empty (0 bytes).", dz);
    return;
  }
  stagedSourceFile = file;
  document.getElementById("sample-dataset-select").value = "";
  const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
  const ext = file.name.split(".").pop().toUpperCase();
  document.getElementById("source-status-text").textContent = file.name;
  document.getElementById("source-status-meta").textContent = `${sizeMb} MB | ${ext}`;
  document.getElementById("source-format-pill").textContent = ext;
  updatePreflightStatus();
}

function handleContractFileStaged(file) {
  if (!file || file.size === 0) {
    const dz = document.getElementById("contract-dropzone");
    triggerHapticFeedback(dz);
    showGlobalError("EMPTY FILE", "The selected contract file is empty (0 bytes).", dz);
    return;
  }
  stagedContractFile = file;
  const sizeKb = (file.size / 1024).toFixed(1);
  document.getElementById("contract-status-text").textContent = file.name;
  document.getElementById("contract-status-meta").textContent = `${sizeKb} KB | JSON`;
  updatePreflightStatus();
}

function updatePreflightStatus() {
  const sourceReady = stagedSourceFile || document.getElementById("sample-dataset-select").value;
  let contractReady = false;

  if (activeContractTab === "sample") {
    contractReady = Boolean(document.getElementById("sample-contract-select").value);
  } else if (activeContractTab === "upload") {
    contractReady = Boolean(stagedContractFile);
  } else if (activeContractTab === "paste") {
    const text = document.getElementById("contract-text-area").value.trim();
    if (text) {
      try {
        JSON.parse(text);
        contractReady = true;
      } catch (_) {
        contractReady = false;
      }
    }
  }

  const pfSource = document.getElementById("pf-source-encoding");
  const pfTarget = document.getElementById("pf-target-schema");
  const btnAssess = document.getElementById("btn-assess");

  if (pfSource) {
    if (sourceReady) {
      pfSource.className = "preflight-item valid";
      pfSource.textContent = "• Source: Staged & Ready (UTF-8 / Delimiter Auto-detect)";
    } else {
      pfSource.className = "preflight-item text-muted";
      pfSource.textContent = "• Source: Waiting for dataset";
    }
  }

  if (pfTarget) {
    if (contractReady) {
      pfTarget.className = "preflight-item valid";
      pfTarget.textContent = "• Target: Schema Contract Validated";
    } else {
      pfTarget.className = "preflight-item text-muted";
      pfTarget.textContent = "• Target: Waiting for valid contract";
    }
  }

  // Apple-style clean status indicator
  const statusLabel = document.getElementById("ingest-status-label");
  const statusDot = document.getElementById("ingest-status-dot");
  if (statusLabel && statusDot) {
    if (sourceReady && contractReady) {
      statusDot.className = "status-dot ready";
      statusLabel.className = "ingest-status-ready";
      statusLabel.textContent = "Source dataset and contract schema ready for inspection";
    } else if (sourceReady && !contractReady) {
      statusDot.className = "status-dot waiting";
      statusLabel.className = "text-muted";
      statusLabel.textContent = "Source staged • Select target schema contract to continue";
    } else if (!sourceReady && contractReady) {
      statusDot.className = "status-dot waiting";
      statusLabel.className = "text-muted";
      statusLabel.textContent = "Contract staged • Select or drop source dataset to continue";
    } else {
      statusDot.className = "status-dot";
      statusLabel.className = "text-muted";
      statusLabel.textContent = "Stage a source dataset and target contract schema to continue";
    }
  }

  if (btnAssess) {
    btnAssess.disabled = !(sourceReady && contractReady);
  }

  updateDynamicIsland();
  updatePreflightPeek();
}

// =============================================================================
// Feature: Instant Pre-flight Quick Peek (Screen 01)
// =============================================================================

function initPreflightPeek() {
  const toggleBtn = document.getElementById("btn-toggle-preflight-peek");
  const card = document.getElementById("preflight-peek-container");
  if (toggleBtn && card) {
    toggleBtn.addEventListener("click", () => {
      card.classList.toggle("is-collapsed");
      SoundEngine.playClick();
    });
  }
}

function updatePreflightPeek() {
  const container = document.getElementById("preflight-peek-container");
  if (!container) return;

  const dsSelect = document.getElementById("sample-dataset-select");
  const cSelect = document.getElementById("sample-contract-select");
  const cText = document.getElementById("contract-text-area");

  const hasSource = Boolean(stagedSourceFile || (dsSelect && dsSelect.value));
  const hasContract = Boolean(
    stagedContractFile ||
    (cSelect && cSelect.value) ||
    (cText && cText.value.trim())
  );

  if (!hasSource && !hasContract) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");

  // Render Source Quick Peek
  renderPreflightSourcePeek();
  // Render Contract Quick Peek
  renderPreflightContractPeek();
}

function renderPreflightSourcePeek() {
  const wrap = document.getElementById("peek-source-table-wrap");
  if (!wrap) return;

  if (stagedSourceFile) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      renderSampleTextInPeek(text, stagedSourceFile.name);
    };
    reader.readAsText(stagedSourceFile.slice(0, 8192));
  } else {
    const dsSelect = document.getElementById("sample-dataset-select");
    const dsId = dsSelect ? dsSelect.value : "";
    if (dsId && sampleDatasetsMap[dsId]) {
      const ds = sampleDatasetsMap[dsId];
      wrap.innerHTML = `
        <div style="padding: 10px; font-size: 11px; font-family: var(--font-mono); color: var(--recon-text-secondary);">
          <div style="font-weight: 600; color: var(--recon-text-primary); margin-bottom: 4px;">Fixture: ${escapeHtml(ds.file_name)}</div>
          <div>Format: <span class="badge badge-indigo">${escapeHtml(ds.format.toUpperCase())}</span> • Ready for profiling</div>
          <div style="margin-top: 6px; font-size: 10px; color: var(--recon-text-muted);">First 3 records and statistical distributions will be computed during assessment.</div>
        </div>
      `;
    } else {
      wrap.innerHTML = `<span class="text-muted font-mono" style="padding: 10px; display: block; font-size: 11px;">Waiting for source staging...</span>`;
    }
  }
}

function renderSampleTextInPeek(rawText, fileName) {
  const wrap = document.getElementById("peek-source-table-wrap");
  if (!wrap || !rawText) return;

  const lines = rawText.trim().split(/\r?\n/).filter(l => l.trim().length > 0);
  if (lines.length > 0) {
    const headerLine = lines[0];
    const isJson = headerLine.startsWith("{") || headerLine.startsWith("[");

    if (isJson) {
      wrap.innerHTML = `<pre style="margin: 0; padding: 8px; font-size: 10px; color: var(--recon-text-secondary); max-height: 120px; overflow: auto;">${escapeHtml(lines.slice(0, 3).join("\n"))}</pre>`;
    } else {
      const delim = headerLine.includes("\t") ? "\t" : ",";
      const headers = headerLine.split(delim).map(h => h.trim().replace(/^["']|["']$/g, ""));
      const rows = lines.slice(1, 4).map(l => l.split(delim).map(c => c.trim().replace(/^["']|["']$/g, "")));

      let tableHtml = `<table class="peek-mini-table"><thead><tr>`;
      headers.slice(0, 6).forEach(h => {
        tableHtml += `<th>${escapeHtml(h)}</th>`;
      });
      if (headers.length > 6) tableHtml += `<th>+${headers.length - 6} more</th>`;
      tableHtml += `</tr></thead><tbody>`;

      rows.forEach(r => {
        tableHtml += `<tr>`;
        r.slice(0, 6).forEach(val => {
          tableHtml += `<td>${escapeHtml(val || "-")}</td>`;
        });
        if (headers.length > 6) tableHtml += `<td>...</td>`;
        tableHtml += `</tr>`;
      });
      tableHtml += `</tbody></table>`;
      wrap.innerHTML = tableHtml;
    }
  }
}

function renderPreflightContractPeek() {
  const wrap = document.getElementById("peek-target-pills-wrap");
  if (!wrap) return;

  let contractObj = null;

  if (activeContractTab === "sample") {
    const cSelect = document.getElementById("sample-contract-select");
    const cId = cSelect ? cSelect.value : "";
    if (cId && sampleContractsMap[cId] && sampleContractsMap[cId].content) {
      try { contractObj = JSON.parse(sampleContractsMap[cId].content); } catch (_) {}
    }
  } else if (activeContractTab === "paste") {
    const text = (document.getElementById("contract-text-area") && document.getElementById("contract-text-area").value.trim()) || "";
    if (text) {
      try { contractObj = JSON.parse(text); } catch (_) {}
    }
  }

  if (contractObj) {
    if (contractObj.fields) {
      const entries = Object.entries(contractObj.fields);
      let pillsHtml = entries.map(([name, f]) => {
        const isReq = Boolean(f.required);
        const type = f.type || "any";
        return `<span class="peek-field-pill ${isReq ? "is-required" : ""}">${isReq ? '<span style="color:var(--recon-rose-text); font-weight:700;">*</span> ' : ""}${escapeHtml(name)} <span class="text-muted" style="font-size:9px;">(${escapeHtml(type)})</span></span>`;
      }).join("");
      wrap.innerHTML = pillsHtml || `<span class="text-muted font-mono" style="font-size:11px;">0 fields defined</span>`;
      return;
    }

    if (contractObj.properties) {
      const requiredList = Array.isArray(contractObj.required) ? contractObj.required : [];
      const entries = Object.entries(contractObj.properties);
      let pillsHtml = entries.map(([name, f]) => {
        const isReq = requiredList.includes(name);
        const type = f.type || "any";
        return `<span class="peek-field-pill ${isReq ? "is-required" : ""}">${isReq ? '<span style="color:var(--recon-rose-text); font-weight:700;">*</span> ' : ""}${escapeHtml(name)} <span class="text-muted" style="font-size:9px;">(${escapeHtml(type)})</span></span>`;
      }).join("");
      wrap.innerHTML = pillsHtml || `<span class="text-muted font-mono" style="font-size:11px;">0 properties</span>`;
      return;
    }
  }

  wrap.innerHTML = `<span class="text-muted font-mono" style="font-size: 11px;">Waiting for contract schema...</span>`;
}

// =============================================================================
// Assessment Workflow (01 Ingest -> 02 Profile & 03 Map)
// =============================================================================

function bindActions() {
  const brandHomeLink = document.getElementById("brand-home-link");
  if (brandHomeLink) {
    brandHomeLink.addEventListener("click", (e) => {
      e.preventDefault();
      navigateToStep(1);
    });
  }

  document.getElementById("btn-assess").addEventListener("click", handleAssessIntegration);
  document.getElementById("btn-approve").addEventListener("click", handleApproveAndGenerate);
  document.getElementById("btn-copy-code").addEventListener("click", handleCopyCode);
  document.getElementById("ack-checkbox").addEventListener("change", updateApprovalGateState);

  const ingestSpecInput = document.getElementById("ingest-mapping-spec-input");
  if (ingestSpecInput) {
    ingestSpecInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        stagedMappingSpecFile = e.target.files[0];
        document.getElementById("ingest-mapping-spec-name").textContent = stagedMappingSpecFile.name;
      }
    });
  }

  const mapSpecInput = document.getElementById("map-spec-upload-input");
  if (mapSpecInput) {
    mapSpecInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleUploadMappingSpecInStudio(e.target.files[0]);
      }
    });
  }

  const btnDismissBanner = document.getElementById("btn-dismiss-spec-banner");
  if (btnDismissBanner) {
    btnDismissBanner.addEventListener("click", () => {
      document.getElementById("mapping-spec-banner").classList.add("hidden");
    });
  }
}

async function handleAssessIntegration() {
  hideGlobalError();
  const formData = new FormData();

  if (stagedSourceFile) {
    formData.append("source_file", stagedSourceFile);
  } else {
    const dsId = document.getElementById("sample-dataset-select").value;
    if (dsId) formData.append("sample_dataset_id", dsId);
  }

  if (activeContractTab === "sample") {
    const cId = document.getElementById("sample-contract-select").value;
    if (cId) formData.append("sample_contract_id", cId);
  } else if (activeContractTab === "upload") {
    if (stagedContractFile) formData.append("contract_file", stagedContractFile);
  } else if (activeContractTab === "paste") {
    const text = document.getElementById("contract-text-area").value.trim();
    if (text) formData.append("contract_text", text);
  }

  if (stagedMappingSpecFile) {
    formData.append("mapping_spec_file", stagedMappingSpecFile);
  }

  const openapiSelect = document.getElementById("openapi-schema-select");
  if (openapiSelect && openapiSelect.value) {
    formData.append("schema_name", openapiSelect.value);
  }

  const btn = document.getElementById("btn-assess");
  const spinner = document.getElementById("assess-spinner");
  btn.disabled = true;
  spinner.classList.remove("hidden");

  try {
    const res = await fetch("/api/assess", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      if (res.status === 404) {
        showSessionLostModal();
        return;
      }
      showGlobalError("ASSESSMENT FAILED", data.detail || "Unable to inspect and profile dataset.", btn);
      return;
    }

    currentSessionId = data.session_id;
    currentAssessment = data;
    mappingOverrides = {};

    // Update Header Capsule
    const headerPulse = document.getElementById("header-pulse");
    if (headerPulse) headerPulse.classList.add("active");
    const sessionDisplay = document.getElementById("session-id-display");
    if (sessionDisplay) sessionDisplay.textContent = currentSessionId.slice(0, 12);
    const contractCapsule = document.getElementById("contract-capsule");
    if (contractCapsule) contractCapsule.classList.remove("hidden");
    const contractNameDisplay = document.getElementById("contract-name-display");
    if (contractNameDisplay) contractNameDisplay.textContent = data.contract.contract_name;
    const contractVersionPill = document.getElementById("contract-version-pill");
    if (contractVersionPill) contractVersionPill.textContent = `v${data.contract.version}`;

    // Render downstream screens
    renderProfileMatrix(data);
    renderMappingStudio(data);
    renderRiskRadar(data);

    // Audio success feedback
    SoundEngine.playSuccess();

    // Navigate to Profile Matrix (Step 02)
    navigateToStep(2);
  } catch (err) {
    showGlobalError("NETWORK ERROR", err.message, btn);
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
  }
}

// =============================================================================
// Screen B: Profile Matrix Rendering
// =============================================================================

function renderProfileMatrix(data) {
  const profile = data.source;
  document.getElementById("profile-summary-line").textContent =
    `File: ${profile.file_name} | Total Records Sampled: ${Number(profile.total_rows).toLocaleString()} | Inferred Columns: ${profile.total_columns} | Duplicates: ${profile.duplicate_rows_count}`;
  document.getElementById("prof-sha-display").textContent = (profile.fingerprint || "").slice(0, 16) + "...";

  const tbody = document.getElementById("profile-tbody");
  tbody.innerHTML = "";

  const colNames = profile.columns;
  colNames.forEach((colName, index) => {
    const colInfo = profile.columns_profile[colName];
    const tr = document.createElement("tr");
    tr.dataset.index = index;
    tr.dataset.column = colName;

    // Field Name
    const tdName = document.createElement("td");
    tdName.innerHTML = `<span class="font-mono" style="font-weight:600; color:var(--recon-text-primary);">${escapeHtml(colName)}</span>`;

    // Type Inferred
    const tdType = document.createElement("td");
    const tBadgeClass = colInfo.inferred_type === "mixed" ? "badge-type type-mixed" : "badge-type";
    tdType.innerHTML = `<span class="${tBadgeClass}">${escapeHtml(colInfo.inferred_type)}</span>`;

    // Nullity Micro-Bar (44px visual bar)
    const tdBar = document.createElement("td");
    const nullPct = colInfo.null_percentage || 0;
    const filledPct = Math.max(0, 100 - nullPct);
    const nullColorClass = nullPct === 0 ? "" : nullPct <= 10 ? "amber" : "rose";
    tdBar.innerHTML = `
      <div class="nullity-cell">
        <div class="nullity-microbar">
          <div class="nullity-filled" style="width: ${filledPct}%;"></div>
          <div class="nullity-null ${nullColorClass}" style="width: ${nullPct}%;"></div>
        </div>
      </div>
    `;

    // Null Count (%)
    const tdNull = document.createElement("td");
    tdNull.className = "font-mono";
    tdNull.innerHTML = `${colInfo.null_count} <span class="text-muted">(${nullPct}%)</span>`;

    // Distinct Count
    const tdDistinct = document.createElement("td");
    tdDistinct.className = "font-mono";
    tdDistinct.textContent = Number(colInfo.distinct_count).toLocaleString();

    // Sample Values
    const tdSamples = document.createElement("td");
    const samplePills = (colInfo.sample_values || [])
      .slice(0, 2)
      .map(v => `<span class="badge badge-muted font-mono" style="margin-right:4px;">${escapeHtml(String(v))}</span>`)
      .join("");
    tdSamples.innerHTML = samplePills || `<span class="text-muted font-mono">-</span>`;

    // Quality / Anomaly Flag
    const tdFlag = document.createElement("td");
    if (colInfo.inferred_type === "mixed") {
      tdFlag.innerHTML = `<span class="badge badge-rose">[ALERT] Mixed Types</span>`;
    } else if (nullPct > 10) {
      tdFlag.innerHTML = `<span class="badge badge-amber">[WARN] High Nullity</span>`;
    } else if (colInfo.distinct_count === profile.total_rows && profile.total_rows > 1) {
      tdFlag.innerHTML = `<span class="badge badge-emerald">[CLEAN] Strict Unique Key</span>`;
    } else {
      tdFlag.innerHTML = `<span class="badge badge-muted">[CLEAN] Nominal</span>`;
    }

    tr.appendChild(tdName);
    tr.appendChild(tdType);
    tr.appendChild(tdBar);
    tr.appendChild(tdNull);
    tr.appendChild(tdDistinct);
    tr.appendChild(tdSamples);
    tr.appendChild(tdFlag);

    tr.addEventListener("click", () => {
      selectProfileRow(index, colName, colInfo, true);
    });

    tbody.appendChild(tr);
  });

  // Select first column initially without forcibly opening the drawer
  if (colNames.length > 0) {
    selectProfileRow(0, colNames[0], profile.columns_profile[colNames[0]], false);
  }
}

function selectProfileRow(index, colName, colInfo, openDrawer = true) {
  selectedProfileIndex = index;
  const rows = document.querySelectorAll("#profile-tbody tr");
  rows.forEach((r, idx) => r.classList.toggle("is-selected", idx === index));

  // Update Drawer
  openDrawerForColumn(colName, colInfo, openDrawer);
}

// =============================================================================
// Screen C: Mapping Review Studio (The 6 Visual States)
// =============================================================================

function renderMappingStudio(data) {
  const proposals = data.proposals || [];
  const sourceColumns = data.source.columns || [];
  const tbody = document.getElementById("mappings-tbody");
  tbody.innerHTML = "";

  const duplicates = getDuplicateSourceAssignments();

  proposals.forEach((prop, index) => {
    const tr = document.createElement("tr");
    tr.className = "mapping-row";
    tr.dataset.index = index;
    tr.dataset.target = prop.target_field;

    // Determine one of the 6 explicit visual states:
    // 1. Approved: User manual override or verified exact match
    // 2. Proposed: Heuristic suggestion from engine
    // 3. Ambiguous: Multiple candidate matches
    // 4. Unresolved: Optional target field with no match
    // 5. Type Conflict: Incompatible source type and target type
    // 6. Missing Required: Required field with no source mapped (BLOCKED)
    const currentChosen = mappingOverrides[prop.target_field] !== undefined
      ? mappingOverrides[prop.target_field]
      : (prop.proposed_source_field || "");

    const isRequired = prop.required === true;
    const isDup = currentChosen && (duplicates.get(currentChosen) || []).length > 1;
    let visualState = "proposed";

    if (!currentChosen && isRequired) {
      visualState = "missing-req";
    } else if (!currentChosen && !isRequired) {
      visualState = "unresolved";
    } else if (isDup) {
      visualState = "conflict";
    } else if (mappingOverrides[prop.target_field]) {
      visualState = "approved";
    } else if (prop.status === "ambiguous" || (prop.evidence && prop.evidence.some(e => e.includes("Multiple")))) {
      visualState = "ambiguous";
    } else if (prop.mapping_type === "transformation_required" || (prop.evidence && prop.evidence.some(e => e.includes("Type conflict") || e.includes("requires cast")))) {
      visualState = "conflict";
    } else {
      visualState = "proposed";
    }

    tr.classList.add(`state-${visualState}`);

    // Col 1: Target Contract Field
    const tdTarget = document.createElement("td");
    const reqBadge = isRequired
      ? `<span class="badge badge-rose" style="font-size:9px;">REQUIRED</span>`
      : `<span class="badge badge-muted" style="font-size:9px;">OPTIONAL</span>`;
    const typeBadge = `<span class="badge badge-type">${escapeHtml(prop.target_type)}</span>`;
    tdTarget.innerHTML = `
      <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
        <span class="font-mono" style="font-weight:600; font-size:13px; color:var(--recon-text-primary);">${escapeHtml(prop.target_field)}</span>
        ${typeBadge}
        ${reqBadge}
      </div>
      <div class="text-secondary" style="font-size:11px; margin-top:3px; line-height:1.4;">${escapeHtml(prop.description || "Target schema field.")}</div>
    `;

    // Col 2: Arrow
    const tdArrow = document.createElement("td");
    tdArrow.className = "mapping-arrow";
    tdArrow.style.textAlign = "center";
    tdArrow.textContent = "◄──";

    // Col 3: Source Column Decision / Override Dropdown
    const tdSource = document.createElement("td");
    const select = document.createElement("select");
    select.className = "mapping-select source-field-box";
    select.dataset.target = prop.target_field;
    select.dataset.required = isRequired ? "true" : "false";

    const optNone = document.createElement("option");
    optNone.value = "";
    optNone.textContent = isRequired ? "-- [ MISSING REQUIRED FIELD ] --" : "-- [ Unmapped / Skip ] --";
    select.appendChild(optNone);

    sourceColumns.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      if (currentChosen === c) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    select.addEventListener("change", e => {
      handleMappingChange(prop.target_field, e.target.value);
    });

    tdSource.appendChild(select);

    // Col 4: Confidence / Heuristic & Diagnostics
    const tdHeuristic = document.createElement("td");
    let heuristicPill = `<span class="badge badge-muted" style="font-size:10px;">${escapeHtml(prop.mapping_type || "HEURISTIC")}</span>`;
    let detailNote = "";

    const alts = prop.alternative_candidates || [];
    const candCount = alts.length > 0 ? (1 + alts.length) : (visualState === "ambiguous" ? 2 : 0);

    if (visualState === "missing-req") {
      heuristicPill = `<span class="badge badge-rose" style="font-size:10px;">NO CANDIDATE</span>`;
      detailNote = `<div class="text-rose" style="font-size:10px; margin-top:3px; font-family:var(--font-mono); line-height:1.3;">Action required: select source column</div>`;
    } else if (isDup) {
      const otherTargets = (duplicates.get(currentChosen) || []).filter(t => t !== prop.target_field);
      heuristicPill = `<span class="badge badge-amber" style="font-size:10px;">DUPLICATE SOURCE</span>`;
      detailNote = `<div class="text-amber" style="font-size:10px; margin-top:3px; font-family:var(--font-mono); line-height:1.3;">Reused in: ${escapeHtml(otherTargets.join(", "))}</div>`;
    } else if (candCount > 1) {
      heuristicPill = `<span class="badge badge-amber" style="font-size:10px;">AMBIGUOUS (${candCount})</span>`;
      detailNote = `<div class="text-amber" style="font-size:10px; margin-top:3px; font-family:var(--font-mono); line-height:1.3;">${candCount} candidate columns found — manual selection required</div>`;
    } else if (prop.mapping_type === "transformation_required" || visualState === "conflict") {
      heuristicPill = `<span class="badge badge-amber" style="font-size:10px;">TRANSFORM REQUIRED</span>`;
      const transformEv = (prop.evidence || []).find(e => e.includes("requires cast") || e.includes("Type conflict") || e.includes("uppercase"));
      if (transformEv) {
        detailNote = `<div class="text-amber" style="font-size:10px; margin-top:3px; font-family:var(--font-mono); line-height:1.3;">${escapeHtml(transformEv)}</div>`;
      }
    } else if (prop.mapping_type === "direct") {
      heuristicPill = `<span class="badge badge-emerald" style="font-size:10px;">DIRECT MATCH</span>`;
    } else if (visualState === "ambiguous") {
      heuristicPill = `<span class="badge badge-amber" style="font-size:10px;">AMBIGUOUS</span>`;
      detailNote = `<div class="text-amber" style="font-size:10px; margin-top:3px; font-family:var(--font-mono); line-height:1.3;">Manual selection required</div>`;
    }
    tdHeuristic.innerHTML = `<div>${heuristicPill}${detailNote}</div>`;

    // Col 5: Status Pill
    const tdStatus = document.createElement("td");
    tdStatus.className = "status-col";
    let statusPillHtml = "";

    if (isDup) {
      statusPillHtml = `<span class="badge status-pill badge-amber">DUPLICATE</span>`;
    } else {
      switch (visualState) {
        case "approved":
          statusPillHtml = `<span class="badge status-pill badge-emerald">APPROVED</span>`;
          break;
        case "proposed":
          statusPillHtml = `<span class="badge status-pill badge-indigo">PROPOSED</span>`;
          break;
        case "ambiguous":
          statusPillHtml = `<span class="badge status-pill badge-amber">AMBIGUOUS</span>`;
          break;
        case "unresolved":
          statusPillHtml = `<span class="badge status-pill badge-muted">UNRESOLVED</span>`;
          break;
        case "conflict":
          statusPillHtml = `<span class="badge status-pill badge-amber">TYPE CONFLICT</span>`;
          break;
        case "missing-req":
          statusPillHtml = `<span class="badge status-pill badge-rose">CRITICAL BLOCKER</span>`;
          break;
      }
    }
    tdStatus.innerHTML = statusPillHtml;

    tr.appendChild(tdTarget);
    tr.appendChild(tdArrow);
    tr.appendChild(tdSource);
    tr.appendChild(tdHeuristic);
    tr.appendChild(tdStatus);

    tr.addEventListener("click", () => {
      selectMappingRow(index, prop, true);
    });

    tbody.appendChild(tr);
  });

  updateMappingFilterCounts();
  filterMappingsTable();
  renderSchemaFlowGraph(data);

  // Select first mapping initially without forcibly opening the drawer
  if (proposals.length > 0) {
    selectMappingRow(0, proposals[0], false);
  }
}

function selectMappingRow(index, prop, openDrawer = true) {
  selectedMappingIndex = index;
  const rows = document.querySelectorAll("#mappings-tbody tr");
  rows.forEach((r, idx) => r.classList.toggle("is-selected", idx === index));
  openDrawerForMapping(prop, openDrawer);
}

function updateMappingFilterCounts() {
  const rows = document.querySelectorAll("#mappings-tbody tr");
  let total = rows.length;
  let approved = 0;
  let action = 0;

  rows.forEach(r => {
    if (r.classList.contains("state-approved")) approved++;
    if (r.classList.contains("state-missing-req") || r.classList.contains("state-ambiguous") || r.classList.contains("state-conflict")) action++;
  });

  document.getElementById("mf-cnt-all").textContent = total;
  document.getElementById("mf-cnt-approved").textContent = approved;
  document.getElementById("mf-cnt-action").textContent = action;
}

function filterMappingsTable() {
  const rows = document.querySelectorAll("#mappings-tbody tr");
  rows.forEach(r => {
    if (activeMapFilter === "all") {
      r.classList.remove("hidden");
    } else if (activeMapFilter === "approved") {
      r.classList.toggle("hidden", !r.classList.contains("state-approved"));
    } else if (activeMapFilter === "action") {
      const isAction = r.classList.contains("state-missing-req") || r.classList.contains("state-ambiguous") || r.classList.contains("state-conflict") || r.classList.contains("state-unresolved");
      r.classList.toggle("hidden", !isAction);
    }
  });
}

// =============================================================================
// Schema Flow Graph Controller (Visual Lines, Beams & Confidence Bars)
// =============================================================================

let activeMappingView = "flow"; // "flow" | "matrix" (default to interactive flow graph)
let currentHighlightedField = null;
let currentSelectedFlowField = null;
let highlightResetTimer = null;

function queueFlowReset() {
  if (highlightResetTimer) clearTimeout(highlightResetTimer);
  highlightResetTimer = setTimeout(() => {
    resetFlowHighlights();
    highlightResetTimer = null;
  }, 110);
}

function initMappingViewToggle() {
  const btnMatrix = document.getElementById("btn-view-matrix");
  const btnFlow = document.getElementById("btn-view-flow");
  const tableContainer = document.getElementById("mapping-table-view");
  const flowContainer = document.getElementById("mapping-flow-view");

  if (!btnMatrix || !btnFlow) return;

  btnMatrix.addEventListener("click", () => {
    activeMappingView = "matrix";
    btnMatrix.classList.add("active");
    btnFlow.classList.remove("active");
    if (tableContainer) tableContainer.classList.remove("hidden");
    if (flowContainer) flowContainer.classList.add("hidden");
  });

  btnFlow.addEventListener("click", () => {
    activeMappingView = "flow";
    btnFlow.classList.add("active");
    btnMatrix.classList.remove("active");
    if (tableContainer) tableContainer.classList.add("hidden");
    if (flowContainer) flowContainer.classList.remove("hidden");
    requestAnimationFrame(() => {
      updateFlowConnections();
    });
  });

  window.addEventListener("resize", () => {
    if (activeMappingView === "flow" && flowContainer && !flowContainer.classList.contains("hidden")) {
      updateFlowConnections();
    }
  });
}

function getDuplicateSourceAssignments() {
  if (!currentAssessment || !currentAssessment.proposals) return new Map();
  const sourceToTargets = new Map();
  currentAssessment.proposals.forEach(p => {
    const chosen = mappingOverrides[p.target_field] !== undefined
      ? mappingOverrides[p.target_field]
      : (p.proposed_source_field || "");
    if (chosen) {
      if (!sourceToTargets.has(chosen)) sourceToTargets.set(chosen, []);
      sourceToTargets.get(chosen).push(p.target_field);
    }
  });
  return sourceToTargets;
}

function evaluateMappingEvidence(prop, chosenSource) {
  if (!chosenSource) {
    return {
      nameScore: 0,
      nameLabel: "0% (Unmapped)",
      typeScore: 0,
      typeLabel: "0% (Unmapped)",
      patternScore: 0,
      patternLabel: "0% (Unmapped)",
      overallText: prop.required ? "Blocked (Missing Required Field)" : "Unmapped (Optional Field)",
      badgeText: prop.required ? "CRITICAL BLOCKER" : "OPTIONAL SKIP",
      badgeClass: prop.required ? "badge-rose" : "badge-muted",
      isTransform: false,
      isDuplicate: false,
      isAmbiguous: false,
      evidenceSummary: prop.required
        ? ["Target field is required by contract but has no source column assigned."]
        : ["Target field is optional and currently unmapped."],
    };
  }

  // Duplicate Check
  const duplicates = getDuplicateSourceAssignments();
  const assignedTargets = duplicates.get(chosenSource) || [];
  const isDuplicate = assignedTargets.length > 1;

  // Source Profile & Target Contract Definitions
  const colProfile = (currentAssessment?.source?.columns_profile && currentAssessment.source.columns_profile[chosenSource]) || {};
  const srcInferredType = colProfile.inferred_type || (prop.source_inferred_type || "string");
  const tgtField = (currentAssessment?.contract?.fields && currentAssessment.contract.fields[prop.target_field]) || {
    target_type: prop.target_type,
    required: prop.required,
    nullable: prop.nullable,
    allowed_values: prop.allowed_values,
    pattern: prop.pattern,
  };

  // 1. Name Match Score
  const normSrc = chosenSource.toLowerCase().replace(/[^a-z0-9]/g, "");
  const normTgt = prop.target_field.toLowerCase().replace(/[^a-z0-9]/g, "");
  let nameScore = 30;
  let nameLabel = "30% (Manual Assignment)";

  if (normSrc === normTgt) {
    nameScore = 100;
    nameLabel = "100% (Exact Match)";
  } else if (normSrc.includes(normTgt) || normTgt.includes(normSrc)) {
    nameScore = 80;
    nameLabel = "80% (Substring / Synonym Match)";
  } else if (prop.evidence && prop.evidence.some(e => e.includes("synonym") || e.includes("heuristic"))) {
    nameScore = 80;
    nameLabel = "80% (Engine Synonym Rule)";
  } else {
    const srcTokens = chosenSource.toLowerCase().split(/[^a-z0-9]+/);
    const tgtTokens = prop.target_field.toLowerCase().split(/[^a-z0-9]+/);
    const overlap = srcTokens.filter(t => t && tgtTokens.includes(t));
    if (overlap.length > 0) {
      nameScore = 60;
      nameLabel = "60% (Token Overlap)";
    } else {
      nameScore = 30;
      nameLabel = "30% (Manual Assignment)";
    }
  }

  // 2. Type Compatibility Score
  const tgtType = tgtField.target_type || prop.target_type;
  let typeScore = 100;
  let typeLabel = `100% (Compatible: ${tgtType})`;
  let isTransform = false;

  if (tgtType === srcInferredType) {
    typeScore = 100;
    typeLabel = `100% (Exact Type: ${tgtType})`;
  } else if (
    (tgtType === "float" && (srcInferredType === "integer" || srcInferredType === "string")) ||
    (tgtType === "integer" && srcInferredType === "string") ||
    (tgtType === "string" && (srcInferredType === "integer" || srcInferredType === "float" || srcInferredType === "datetime")) ||
    (tgtType === "datetime" && srcInferredType === "string")
  ) {
    typeScore = 80;
    typeLabel = `80% (Cast: ${srcInferredType} → ${tgtType})`;
    isTransform = true;
  } else {
    typeScore = 25;
    typeLabel = `25% (Incompatible: ${srcInferredType} vs ${tgtType})`;
  }

  // 3. Value Pattern Match Score
  let patternScore = 100;
  let patternLabel = "100% (Constraints Satisfied)";

  if (tgtField.allowed_values && tgtField.allowed_values.length > 0) {
    const sampleVals = colProfile.sample_values || [];
    const allowed = new Set(tgtField.allowed_values);
    const matched = sampleVals.filter(s => allowed.has(String(s)) || allowed.has(String(s).toUpperCase()));
    if (sampleVals.length > 0) {
      const matchPct = Math.round((matched.length / sampleVals.length) * 100);
      patternScore = matchPct;
      patternLabel = `${matchPct}% (${matched.length}/${sampleVals.length} Enum Match)`;
      if (matchPct < 100) isTransform = true;
    }
  } else if (!tgtField.nullable && colProfile.null_count > 0) {
    patternScore = 40;
    patternLabel = `40% (Null Risk: ${colProfile.null_percentage}% nulls in non-nullable field)`;
  } else if (colProfile.has_whitespace_anomalies) {
    patternScore = 85;
    patternLabel = "85% (Whitespace Anomalies Detected)";
    isTransform = true;
  }

  // Evidence summary
  const evSummary = (prop.evidence && prop.evidence.length > 0)
    ? [...prop.evidence]
    : [];
  if (mappingOverrides[prop.target_field]) {
    evSummary.unshift(`User override active: mapped to source '${chosenSource}'.`);
  }
  if (isDuplicate) {
    evSummary.push(`DUPLICATE WARNING: Source column '${chosenSource}' is assigned to multiple targets (${assignedTargets.join(", ")}).`);
  }

  // Badges & Labels
  let badgeText = "1:1 DIRECT PASS";
  let badgeClass = "badge-emerald";
  let overallText = "High Confidence (Direct Match)";
  let isAmbiguous = (prop.status === "ambiguous" || (prop.evidence && prop.evidence.some(e => e.includes("Multiple")))) && !mappingOverrides[prop.target_field];

  if (isDuplicate) {
    badgeText = "DUPLICATE ASSIGNMENT";
    badgeClass = "badge-amber";
    overallText = `Warning: Source mapped to ${assignedTargets.length} fields (${assignedTargets.join(", ")})`;
  } else if (isAmbiguous) {
    badgeText = "AMBIGUOUS MATCH";
    badgeClass = "badge-amber";
    overallText = "Ambiguous (Multiple Candidate Sources)";
  } else if (isTransform || prop.mapping_type === "transformation_required") {
    badgeText = "TRANSFORMATION REQUIRED";
    badgeClass = "badge-amber";
    overallText = "Transformation Required (Safe Cast Synthesizable)";
  } else if (mappingOverrides[prop.target_field]) {
    badgeText = "MANUAL OVERRIDE";
    badgeClass = "badge-indigo";
    overallText = "Manual Assignment (User Approved)";
  }

  return {
    nameScore,
    nameLabel,
    typeScore,
    typeLabel,
    patternScore,
    patternLabel,
    overallText,
    badgeText,
    badgeClass,
    isTransform,
    isDuplicate,
    isAmbiguous,
    evidenceSummary: evSummary,
  };
}

function handleMappingChange(targetField, newSourceVal) {
  const val = newSourceVal ? newSourceVal.trim() : "";
  mappingOverrides[targetField] = val;

  // Authoritative Engine & UI Synchronizer:
  // 1. Table Matrix State
  renderMappingStudio(currentAssessment);

  // 2. Risk Radar & Approval Gate
  renderRiskRadar(currentAssessment);

  // 3. Flow Graph Nodes, State Badges & Counters
  updateFlowGraphState(currentAssessment);

  // 4. SVG Connections & Transformer Chips
  updateFlowConnections();

  // 5. Trace Inspector & Confidence Micro-Bars
  highlightFlowStream(targetField, false);

  // 6. Dynamic Health Island Status
  updateDynamicIsland();
}

function renderSchemaFlowGraph(data) {
  if (!data) return;

  const proposals = data.proposals || [];
  const sourceColumns = data.source.columns || [];
  const profileFields = (data.source && (data.source.columns_profile || (data.source.profile && data.source.profile.fields))) || {};

  const srcNodesContainer = document.getElementById("flow-source-nodes");
  const tgtNodesContainer = document.getElementById("flow-target-nodes");
  if (!srcNodesContainer || !tgtNodesContainer) return;

  srcNodesContainer.innerHTML = "";
  tgtNodesContainer.innerHTML = "";

  const duplicates = getDuplicateSourceAssignments();
  const mappedSourceCols = new Set();
  let directCount = 0;
  let transformCount = 0;
  let blockerCount = 0;

  proposals.forEach(p => {
    const chosen = mappingOverrides[p.target_field] !== undefined ? mappingOverrides[p.target_field] : (p.proposed_source_field || "");
    if (chosen) {
      mappedSourceCols.add(chosen);
      const ev = evaluateMappingEvidence(p, chosen);
      if (ev.isTransform || p.mapping_type === "transformation_required") transformCount++;
      else directCount++;
    } else if (p.required) {
      blockerCount++;
    }
  });

  const discardCount = Math.max(0, sourceColumns.length - mappedSourceCols.size);

  // Update Toolbar counters
  const elDirect = document.getElementById("fl-cnt-direct");
  const elTransform = document.getElementById("fl-cnt-transform");
  const elBlocker = document.getElementById("fl-cnt-blocker");
  const elDiscard = document.getElementById("fl-cnt-discard");
  const elSrcBadge = document.getElementById("flow-src-count-badge");
  const elTgtBadge = document.getElementById("flow-tgt-count-badge");

  if (elDirect) elDirect.textContent = directCount;
  if (elTransform) elTransform.textContent = transformCount;
  if (elBlocker) elBlocker.textContent = blockerCount;
  if (elDiscard) elDiscard.textContent = discardCount;
  if (elSrcBadge) elSrcBadge.textContent = `${sourceColumns.length} Fields`;
  if (elTgtBadge) elTgtBadge.textContent = `${proposals.length} Fields`;

  // 1. Render Source Nodes
  sourceColumns.forEach(col => {
    const prof = profileFields[col] || {};
    const infType = prof.inferred_type || "string";
    const sampleVal = (prof.sample_values && prof.sample_values.length > 0)
      ? String(prof.sample_values[0])
      : "null";
    const isMapped = mappedSourceCols.has(col);

    const node = document.createElement("div");
    node.className = `flow-node flow-source-node ${isMapped ? "" : "is-discarded"}`;
    node.dataset.col = col;

    node.innerHTML = `
      <div class="flow-node-title-row">
        <span class="flow-node-name">${escapeHtml(col)}</span>
        <span class="badge badge-type">${escapeHtml(infType)}</span>
      </div>
      <div class="flow-node-sample" title="${escapeHtml(sampleVal)}">Sample: "${escapeHtml(sampleVal)}"</div>
      ${isMapped ? '<span class="flow-anchor-dot"></span>' : '<span class="badge badge-muted" style="font-size:9px; margin-top:4px;">Unmapped</span>'}
    `;

    node.addEventListener("mouseenter", () => highlightFlowStreamBySource(col));
    node.addEventListener("mouseleave", () => queueFlowReset());
    node.addEventListener("click", () => {
      const matchedProp = proposals.find(p => {
        const cur = mappingOverrides[p.target_field] !== undefined ? mappingOverrides[p.target_field] : p.proposed_source_field;
        return cur === col;
      });
      if (matchedProp) {
        highlightFlowStream(matchedProp.target_field, true);
      }
    });

    srcNodesContainer.appendChild(node);
  });

  // 2. Render Target Nodes
  proposals.forEach((prop, idx) => {
    const currentChosen = mappingOverrides[prop.target_field] !== undefined
      ? mappingOverrides[prop.target_field]
      : (prop.proposed_source_field || "");

    const isReq = prop.required === true;
    const isBlocked = isReq && !currentChosen;
    const isDup = currentChosen && (duplicates.get(currentChosen) || []).length > 1;
    const ev = evaluateMappingEvidence(prop, currentChosen);

    const node = document.createElement("div");
    node.className = `flow-node flow-target-node ${isBlocked ? "is-blocked" : ""}`;
    node.dataset.field = prop.target_field;
    node.dataset.index = idx;

    const reqBadge = isReq
      ? `<span class="badge badge-rose" style="font-size:9px;">REQUIRED</span>`
      : `<span class="badge badge-muted" style="font-size:9px;">OPTIONAL</span>`;

    let statePill = "";
    if (isBlocked) {
      statePill = `<span class="badge badge-rose" style="font-size:9px; animation: reconRosePulse 2s infinite ease-in-out;">MISSING REQ</span>`;
    } else if (isDup) {
      statePill = `<span class="badge badge-amber" style="font-size:9px;">DUPLICATE</span>`;
    } else if (ev.badgeText === "AMBIGUOUS MATCH") {
      statePill = `<span class="badge badge-amber" style="font-size:9px;">AMBIGUOUS</span>`;
    } else if (ev.isTransform || prop.mapping_type === "transformation_required") {
      statePill = `<span class="badge badge-amber" style="font-size:9px;">TRANSFORM</span>`;
    } else if (mappingOverrides[prop.target_field]) {
      statePill = `<span class="badge badge-indigo" style="font-size:9px;">APPROVED</span>`;
    } else {
      statePill = `<span class="badge badge-emerald" style="font-size:9px;">DIRECT</span>`;
    }

    node.innerHTML = `
      <div class="flow-node-title-row">
        <span class="flow-node-name">${escapeHtml(prop.target_field)}</span>
        <div style="display:flex; align-items:center; gap:4px;">
          ${reqBadge}
          <span class="badge badge-type">${escapeHtml(prop.target_type)}</span>
        </div>
      </div>
      <div style="margin-top:8px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:4px;">
          <span class="font-mono text-muted" style="font-size:10px; font-weight:600;">SOURCE COLUMN:</span>
          <span class="flow-node-state-pill">${statePill}</span>
        </div>
        <select class="form-select flow-target-select font-mono" data-target="${escapeHtml(prop.target_field)}" style="font-size:11px; height:30px; padding:3px 8px; width:100%; background-color:var(--recon-bg-root); border-color:var(--recon-border-default);">
          <option value="">${isReq ? '-- [ MISSING REQUIRED ] --' : '-- [ Unmapped / Skip ] --'}</option>
          ${sourceColumns.map(col => `<option value="${escapeHtml(col)}"${currentChosen === col ? ' selected' : ''}>${escapeHtml(col)}</option>`).join('')}
        </select>
      </div>
      <span class="flow-anchor-dot"></span>
    `;

    const selectEl = node.querySelector(".flow-target-select");
    if (selectEl) {
      selectEl.addEventListener("click", e => e.stopPropagation());
      selectEl.addEventListener("change", e => {
        handleMappingChange(prop.target_field, e.target.value);
      });
    }

    node.addEventListener("mouseenter", () => highlightFlowStream(prop.target_field, false));
    node.addEventListener("mouseleave", () => queueFlowReset());
    node.addEventListener("click", () => highlightFlowStream(prop.target_field, true));

    tgtNodesContainer.appendChild(node);
  });

  // 3. Draw initial connections and Xcode gutter minimap
  requestAnimationFrame(() => {
    updateFlowConnections();
    renderMinimapGutter(data);
    if (proposals.length > 0) {
      highlightFlowStream(proposals[0].target_field, false);
    }
  });
}

function updateFlowGraphState(data) {
  if (!data || !data.proposals) return;
  const proposals = data.proposals || [];
  const sourceColumns = (data.source && data.source.columns) || [];
  const duplicates = getDuplicateSourceAssignments();

  const mappedSourceCols = new Set();
  let directCount = 0;
  let transformCount = 0;
  let blockerCount = 0;

  proposals.forEach(p => {
    const chosen = mappingOverrides[p.target_field] !== undefined
      ? mappingOverrides[p.target_field]
      : (p.proposed_source_field || "");
    if (chosen) {
      mappedSourceCols.add(chosen);
      const ev = evaluateMappingEvidence(p, chosen);
      if (ev.isTransform || p.mapping_type === "transformation_required") transformCount++;
      else directCount++;
    } else if (p.required) {
      blockerCount++;
    }
  });

  const discardCount = Math.max(0, sourceColumns.length - mappedSourceCols.size);

  const elDirect = document.getElementById("fl-cnt-direct");
  const elTransform = document.getElementById("fl-cnt-transform");
  const elBlocker = document.getElementById("fl-cnt-blocker");
  const elDiscard = document.getElementById("fl-cnt-discard");

  if (elDirect) elDirect.textContent = directCount;
  if (elTransform) elTransform.textContent = transformCount;
  if (elBlocker) elBlocker.textContent = blockerCount;
  if (elDiscard) elDiscard.textContent = discardCount;

  // Update Source Nodes discard/mapped classes
  document.querySelectorAll(".flow-source-node").forEach(node => {
    const col = node.dataset.col;
    const isMapped = mappedSourceCols.has(col);
    node.classList.toggle("is-discarded", !isMapped);
    let dot = node.querySelector(".flow-anchor-dot");
    let unmappedBadge = node.querySelector(".badge-muted");
    if (isMapped && !dot) {
      if (unmappedBadge) unmappedBadge.remove();
      const newDot = document.createElement("span");
      newDot.className = "flow-anchor-dot";
      node.appendChild(newDot);
    } else if (!isMapped && dot) {
      dot.remove();
      const badge = document.createElement("span");
      badge.className = "badge badge-muted";
      badge.style.cssText = "font-size:9px; margin-top:4px;";
      badge.textContent = "Unmapped";
      node.appendChild(badge);
    }
  });

  // Update Target Nodes
  proposals.forEach(prop => {
    const tgtNode = document.querySelector(`.flow-target-node[data-field="${CSS.escape(prop.target_field)}"]`);
    if (!tgtNode) return;

    const chosen = mappingOverrides[prop.target_field] !== undefined
      ? mappingOverrides[prop.target_field]
      : (prop.proposed_source_field || "");

    const isReq = prop.required === true;
    const isBlocked = isReq && !chosen;
    const isDup = chosen && (duplicates.get(chosen) || []).length > 1;
    const ev = evaluateMappingEvidence(prop, chosen);

    tgtNode.classList.toggle("is-blocked", isBlocked);

    const selectEl = tgtNode.querySelector(".flow-target-select");
    if (selectEl && selectEl.value !== chosen) {
      selectEl.value = chosen;
    }

    const statePillContainer = tgtNode.querySelector(".flow-node-state-pill");
    if (statePillContainer) {
      let statePill = "";
      if (isBlocked) {
        statePill = `<span class="badge badge-rose" style="font-size:9px; animation: reconRosePulse 2s infinite ease-in-out;">MISSING REQ</span>`;
      } else if (isDup) {
        statePill = `<span class="badge badge-amber" style="font-size:9px;">DUPLICATE</span>`;
      } else if (ev.badgeText === "AMBIGUOUS MATCH") {
        statePill = `<span class="badge badge-amber" style="font-size:9px;">AMBIGUOUS</span>`;
      } else if (ev.isTransform || prop.mapping_type === "transformation_required") {
        statePill = `<span class="badge badge-amber" style="font-size:9px;">TRANSFORM</span>`;
      } else if (mappingOverrides[prop.target_field]) {
        statePill = `<span class="badge badge-indigo" style="font-size:9px;">APPROVED</span>`;
      } else {
        statePill = `<span class="badge badge-emerald" style="font-size:9px;">DIRECT</span>`;
      }
      statePillContainer.innerHTML = statePill;
    }
  });

  renderMinimapGutter(data);
}

function renderMinimapGutter(data) {
  const track = document.getElementById("minimap-track");
  if (!track || !data || !data.proposals) return;

  track.innerHTML = "";
  const duplicates = getDuplicateSourceAssignments();

  data.proposals.forEach((prop, idx) => {
    const chosen = mappingOverrides[prop.target_field] !== undefined
      ? mappingOverrides[prop.target_field]
      : (prop.proposed_source_field || "");

    const isReq = prop.required === true;
    const isBlocked = isReq && !chosen;
    const isDup = chosen && (duplicates.get(chosen) || []).length > 1;
    const ev = evaluateMappingEvidence(prop, chosen);

    let markerClass = "marker-direct";
    let markerState = "1:1 Direct";

    if (isBlocked) {
      markerClass = "marker-blocker";
      markerState = "Blocker: Required Unmapped";
    } else if (mappingOverrides[prop.target_field]) {
      markerClass = "marker-approved";
      markerState = "Approved Human Override";
    } else if (isDup) {
      markerClass = "marker-transform";
      markerState = "Duplicate Source Assignment";
    } else if (ev.badgeText === "AMBIGUOUS MATCH") {
      markerClass = "marker-transform";
      markerState = "Ambiguous Match";
    } else if (ev.isTransform || prop.mapping_type === "transformation_required") {
      markerClass = "marker-transform";
      markerState = "Transformation Required";
    }

    const marker = document.createElement("div");
    marker.className = `minimap-marker ${markerClass}`;
    marker.dataset.target = prop.target_field;
    marker.dataset.idx = idx;
    marker.title = `${prop.target_field} [${markerState}]`;

    marker.addEventListener("click", () => {
      highlightFlowStream(prop.target_field, true);
      const tgtNode = document.querySelector(`.flow-target-node[data-field="${CSS.escape(prop.target_field)}"]`);
      if (tgtNode) {
        tgtNode.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });

    marker.addEventListener("mouseenter", () => {
      highlightFlowStream(prop.target_field, false);
    });

    marker.addEventListener("mouseleave", () => {
      queueFlowReset();
    });

    track.appendChild(marker);
  });
}

function updateFlowConnections() {
  const flowContainer = document.getElementById("mapping-flow-view");
  if (!flowContainer || flowContainer.classList.contains("hidden")) return;

  const svgCanvas = document.getElementById("flow-svg-canvas");
  const chipsLayer = document.getElementById("flow-chips-layer");
  if (!svgCanvas || !chipsLayer) return;

  svgCanvas.innerHTML = "";
  chipsLayer.innerHTML = "";

  if (!currentAssessment || !currentAssessment.proposals) return;

  const svgRect = svgCanvas.getBoundingClientRect();
  if (svgRect.width === 0 || svgRect.height === 0) return;

  const duplicates = getDuplicateSourceAssignments();

  currentAssessment.proposals.forEach(prop => {
    const currentChosen = mappingOverrides[prop.target_field] !== undefined
      ? mappingOverrides[prop.target_field]
      : (prop.proposed_source_field || "");

    if (!currentChosen) return;

    // Find source node anchor
    const srcNode = document.querySelector(`.flow-source-node[data-col="${CSS.escape(currentChosen)}"]`);
    const tgtNode = document.querySelector(`.flow-target-node[data-field="${CSS.escape(prop.target_field)}"]`);

    if (!srcNode || !tgtNode) return;

    const srcDot = srcNode.querySelector(".flow-anchor-dot");
    const tgtDot = tgtNode.querySelector(".flow-anchor-dot");
    if (!srcDot || !tgtDot) return;

    const sRect = srcDot.getBoundingClientRect();
    const tRect = tgtDot.getBoundingClientRect();

    const x1 = sRect.left + sRect.width / 2 - svgRect.left;
    const y1 = sRect.top + sRect.height / 2 - svgRect.top;
    const x2 = tRect.left + tRect.width / 2 - svgRect.left;
    const y2 = tRect.top + tRect.height / 2 - svgRect.top;

    const dx = Math.max(30, Math.abs(x2 - x1) * 0.48);

    const isDup = (duplicates.get(currentChosen) || []).length > 1;
    const ev = evaluateMappingEvidence(prop, currentChosen);
    const isDirect = !isDup && !ev.isTransform && prop.mapping_type === "direct";
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    let strokeColor;
    if (isDup) {
      strokeColor = isDark ? "#FBBF24" : "#F59E0B";
    } else if (mappingOverrides[prop.target_field]) {
      strokeColor = isDark ? "#34D399" : "#059669";
    } else if (isDirect) {
      strokeColor = isDark ? "#38BDF8" : "#2563EB";
    } else {
      strokeColor = isDark ? "#FBBF24" : "#D97706";
    }

    // SVG Curved Path
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
    path.setAttribute("class", "flow-line");
    path.setAttribute("stroke", strokeColor);
    path.setAttribute("stroke-width", isDup ? "2.6" : "2.2");
    path.setAttribute("fill", "none");
    path.dataset.target = prop.target_field;
    path.dataset.source = currentChosen;

    path.addEventListener("mouseenter", () => highlightFlowStream(prop.target_field, false));
    path.addEventListener("mouseleave", () => queueFlowReset());
    path.addEventListener("click", () => highlightFlowStream(prop.target_field, true));

    svgCanvas.appendChild(path);

    // Feature 2: Living data packet particle gliding along wire
    const particle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    particle.setAttribute("r", "3.2");
    particle.setAttribute("fill", strokeColor);
    particle.setAttribute("class", "flow-packet-particle");
    particle.dataset.target = prop.target_field;
    particle.dataset.source = currentChosen;

    const animMotion = document.createElementNS("http://www.w3.org/2000/svg", "animateMotion");
    animMotion.setAttribute("path", `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
    const hash = (prop.target_field || "").split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
    const durSec = (2.6 + (hash % 5) * 0.35).toFixed(2);
    animMotion.setAttribute("dur", `${durSec}s`);
    animMotion.setAttribute("repeatCount", "indefinite");
    animMotion.setAttribute("keyPoints", "0;1");
    animMotion.setAttribute("keyTimes", "0;1");
    animMotion.setAttribute("calcMode", "linear");

    particle.appendChild(animMotion);
    svgCanvas.appendChild(particle);

    // Midpoint Transformer Chip
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;

    const chip = document.createElement("div");
    let chipClass = "flow-chip";
    let chipLabel = "1:1 PASS";

    if (isDup) {
      chipClass += " chip-duplicate";
      chipLabel = "REUSED SOURCE";
    } else if (ev.badgeText === "AMBIGUOUS MATCH") {
      chipClass += " chip-ambiguous";
      chipLabel = "AMBIGUOUS";
    } else if (ev.isTransform || prop.mapping_type === "transformation_required") {
      chipClass += " chip-transform";
      const tgtType = prop.target_type;
      if (tgtType === "datetime" || (prop.evidence && prop.evidence.some(e => e.includes("ISO") || e.includes("date")))) {
        chipLabel = "ISO8601";
      } else if (tgtType === "float" || tgtType === "integer" || (prop.evidence && prop.evidence.some(e => e.includes("cast") || e.includes("float")))) {
        chipLabel = "STRIP & CAST";
      } else {
        chipLabel = "TRANSFORM";
      }
    } else {
      chipClass += " chip-direct";
      chipLabel = "1:1 PASS";
    }

    chip.className = chipClass;
    chip.style.left = `${midX}px`;
    chip.style.top = `${midY}px`;
    chip.dataset.target = prop.target_field;
    chip.textContent = chipLabel;

    chip.addEventListener("mouseenter", () => highlightFlowStream(prop.target_field, false));
    chip.addEventListener("mouseleave", () => queueFlowReset());
    chip.addEventListener("click", () => highlightFlowStream(prop.target_field, true));

    chipsLayer.appendChild(chip);
  });
}

function highlightFlowStream(targetField, selectInDrawer = false) {
  if (highlightResetTimer) {
    clearTimeout(highlightResetTimer);
    highlightResetTimer = null;
  }

  if (selectInDrawer) {
    currentSelectedFlowField = targetField;
  } else if (!currentSelectedFlowField) {
    currentSelectedFlowField = targetField;
  }

  if (currentHighlightedField === targetField && !selectInDrawer) {
    return;
  }
  currentHighlightedField = targetField;
  if (!currentAssessment || !currentAssessment.proposals) return;

  const prop = currentAssessment.proposals.find(p => p.target_field === targetField);
  if (!prop) return;

  const currentChosen = mappingOverrides[prop.target_field] !== undefined
    ? mappingOverrides[prop.target_field]
    : (prop.proposed_source_field || "");

  // Highlight Target Nodes
  document.querySelectorAll(".flow-target-node").forEach(n => {
    n.classList.toggle("active", n.dataset.field === targetField);
  });

  // Highlight Source Nodes
  document.querySelectorAll(".flow-source-node").forEach(n => {
    n.classList.toggle("active", n.dataset.col === currentChosen);
  });

  // Highlight Lines
  document.querySelectorAll(".flow-line").forEach(l => {
    const isMatch = l.dataset.target === targetField;
    l.classList.toggle("active", isMatch);
    l.style.opacity = isMatch ? "1" : "0.15";
  });

  // Highlight Chips
  document.querySelectorAll(".flow-chip").forEach(c => {
    const isMatch = c.dataset.target === targetField;
    c.classList.toggle("active", isMatch);
    c.style.opacity = isMatch ? "1" : "0.2";
  });

  // Highlight Living Particles
  document.querySelectorAll(".flow-packet-particle").forEach(p => {
    const isMatch = p.dataset.target === targetField;
    p.classList.toggle("active", isMatch);
    p.style.opacity = isMatch ? "1" : "0.15";
  });

  // Live Conduit Bubble showing real raw sample data transforming to target
  let conduitBubble = document.getElementById("flow-conduit-bubble");
  if (!conduitBubble) {
    conduitBubble = document.createElement("div");
    conduitBubble.id = "flow-conduit-bubble";
    conduitBubble.className = "flow-conduit-bubble";
    const chipsLayer = document.getElementById("flow-chips-layer");
    if (chipsLayer) chipsLayer.appendChild(conduitBubble);
  }
  const matchingChip = document.querySelector(`.flow-chip[data-target="${CSS.escape(targetField)}"]`);
  if (matchingChip && conduitBubble) {
    let rawVal = "";
    if (currentAssessment && currentAssessment.source) {
      if (currentAssessment.source.columns_profile && currentAssessment.source.columns_profile[currentChosen]) {
        const samples = currentAssessment.source.columns_profile[currentChosen].sample_values;
        if (samples && samples.length > 0) {
          rawVal = String(samples[0]);
        }
      }
      if (!rawVal && currentAssessment.source.sample_rows && currentAssessment.source.sample_rows.length > 0) {
        rawVal = String(currentAssessment.source.sample_rows[0][currentChosen] ?? "");
      }
    }
    const sampleDisplay = rawVal !== "" ? (rawVal.length > 20 ? `"${rawVal.slice(0, 18)}..."` : `"${rawVal}"`) : "null";
    conduitBubble.style.left = matchingChip.style.left;
    conduitBubble.style.top = matchingChip.style.top;
    conduitBubble.innerHTML = `<span style="color:var(--recon-primary-base);font-weight:600;">Sample:</span> ${escapeHtml(sampleDisplay)} &rarr; <span style="color:#30D158;font-weight:600;">${escapeHtml(targetField)}</span>`;
    conduitBubble.classList.remove("hidden");
  } else if (conduitBubble) {
    conduitBubble.classList.add("hidden");
  }

  // Update Meter Panel
  const elConn = document.getElementById("flow-meter-connection");
  const elBadge = document.getElementById("flow-meter-type-badge");
  const elScore = document.getElementById("flow-meter-overall-score");

  const nameVal = document.getElementById("fbar-name-val");
  const nameFill = document.getElementById("fbar-name-fill");
  const typeVal = document.getElementById("fbar-type-val");
  const typeFill = document.getElementById("fbar-type-fill");
  const patVal = document.getElementById("fbar-pattern-val");
  const patFill = document.getElementById("fbar-pattern-fill");
  const elEvidence = document.getElementById("flow-meter-evidence");

  if (elConn) {
    elConn.textContent = currentChosen
      ? `${currentChosen} → ${targetField}`
      : `[UNMAPPED] → ${targetField}`;
  }

  // Derive Scores Strictly from Engine Evidence
  const ev = evaluateMappingEvidence(prop, currentChosen);

  if (elBadge) {
    elBadge.textContent = ev.badgeText;
    elBadge.className = `badge ${ev.badgeClass} font-mono`;
  }
  if (elScore) elScore.textContent = `Confidence: ${ev.overallText}`;

  if (nameVal && nameFill) {
    nameVal.textContent = ev.nameLabel;
    nameFill.style.width = `${ev.nameScore}%`;
  }
  if (typeVal && typeFill) {
    typeVal.textContent = ev.typeLabel;
    typeFill.style.width = `${ev.typeScore}%`;
  }
  if (patVal && patFill) {
    patVal.textContent = ev.patternLabel;
    patFill.style.width = `${ev.patternScore}%`;
  }

  if (elEvidence) {
    if (ev.evidenceSummary && ev.evidenceSummary.length > 0) {
      elEvidence.innerHTML = `<strong>Engine Evidence:</strong> ${ev.evidenceSummary.map(e => escapeHtml(e)).join(" &bull; ")}`;
      elEvidence.classList.remove("hidden");
    } else {
      elEvidence.innerHTML = "";
      elEvidence.classList.add("hidden");
    }
  }

  // Populate Trace Inspector Source Selector
  const overrideWrap = document.getElementById("flow-meter-override-wrap");
  const sourceSelect = document.getElementById("flow-meter-source-select");
  if (overrideWrap && sourceSelect && currentAssessment) {
    overrideWrap.classList.remove("hidden");
    const sourceCols = currentAssessment.source.columns || [];
    sourceSelect.innerHTML = `
      <option value="">${prop.required ? '-- [ MISSING REQUIRED ] --' : '-- [ Unmapped / Skip ] --'}</option>
      ${sourceCols.map(c => `<option value="${escapeHtml(c)}"${currentChosen === c ? ' selected' : ''}>${escapeHtml(c)}</option>`).join('')}
    `;

    sourceSelect.onchange = (e) => {
      handleMappingChange(targetField, e.target.value);
    };
  }

  if (selectInDrawer) {
    openDrawerForMapping(prop, true);
  }
}

function highlightFlowStreamBySource(sourceCol) {
  if (!currentAssessment || !currentAssessment.proposals) return;
  const prop = currentAssessment.proposals.find(p => {
    const cur = mappingOverrides[p.target_field] !== undefined ? mappingOverrides[p.target_field] : p.proposed_source_field;
    return cur === sourceCol;
  });
  if (prop) {
    highlightFlowStream(prop.target_field, false);
  } else {
    document.querySelectorAll(".flow-source-node").forEach(n => {
      n.classList.toggle("active", n.dataset.col === sourceCol);
    });
    document.querySelectorAll(".flow-target-node").forEach(n => n.classList.remove("active"));
    document.querySelectorAll(".flow-line").forEach(l => l.style.opacity = "0.15");
    document.querySelectorAll(".flow-chip").forEach(c => c.style.opacity = "0.2");
  }
}

function resetFlowHighlights() {
  if (highlightResetTimer) {
    clearTimeout(highlightResetTimer);
    highlightResetTimer = null;
  }
  if (currentSelectedFlowField) {
    highlightFlowStream(currentSelectedFlowField, false);
  } else if (currentHighlightedField) {
    highlightFlowStream(currentHighlightedField, false);
  } else {
    document.querySelectorAll(".flow-line").forEach(l => {
      l.classList.remove("active");
      l.style.opacity = "1";
    });
    document.querySelectorAll(".flow-chip").forEach(c => {
      c.classList.remove("active");
      c.style.opacity = "1";
    });
    document.querySelectorAll(".flow-packet-particle").forEach(p => {
      p.classList.remove("active");
      p.style.opacity = "0.85";
    });
    document.querySelectorAll(".flow-node").forEach(n => n.classList.remove("active"));
    const conduitBubble = document.getElementById("flow-conduit-bubble");
    if (conduitBubble) conduitBubble.classList.add("hidden");
  }
}

// =============================================================================
// Screen D: Risk Radar & Approval Gate
// =============================================================================

function renderRiskRadar(data) {
  const blockersContainer = document.getElementById("radar-blockers-container");
  const warningsContainer = document.getElementById("radar-warnings-container");
  blockersContainer.innerHTML = "";
  warningsContainer.innerHTML = "";

  const proposals = data.proposals || [];
  let unmappedRequiredCount = 0;

  // Check unmapped required fields based on current overrides
  proposals.forEach(p => {
    const isReq = p.required === true;
    const chosen = mappingOverrides[p.target_field] !== undefined
      ? mappingOverrides[p.target_field]
      : (p.proposed_source_field || "");
    if (isReq && !chosen) {
      unmappedRequiredCount++;
      const item = document.createElement("div");
      item.className = "risk-card-item blocker";
      item.innerHTML = `
        <div class="risk-card-header">
          <span class="font-mono text-rose" style="font-weight:600;">[ERR_REQ_FIELD_MISSING] Field '${escapeHtml(p.target_field)}' is required but unmapped</span>
          <span class="badge badge-rose">HARD BLOCKER</span>
        </div>
        <div class="text-secondary" style="font-size:12px; margin-top:4px;">
          The target contract specifies '${escapeHtml(p.target_field)}' as a required field with no valid source mapping.
        </div>
        <div class="font-mono" style="font-size:11px; margin-top:6px; color:var(--recon-text-primary);">
          → Suggested Remediation: Open Step 03 (MAP) and map '${escapeHtml(p.target_field)}' to a valid source column.
        </div>
      `;
      blockersContainer.appendChild(item);
    }
  });

  // Render risks from backend
  const backendRisks = data.risks || [];
  backendRisks.forEach(r => {
    const isCritical = r.severity.toLowerCase() === "critical";
    const item = document.createElement("div");
    item.className = `risk-card-item ${isCritical ? "blocker" : "warning"}`;
    item.innerHTML = `
      <div class="risk-card-header">
        <span class="font-mono" style="font-weight:600;">[${escapeHtml(r.rule_id)}] ${escapeHtml(r.rule_name)}</span>
        <span class="badge ${isCritical ? "badge-rose" : "badge-amber"}">${escapeHtml(r.severity)}</span>
      </div>
      <div class="text-secondary" style="font-size:12px; margin-top:4px;">${escapeHtml(r.explanation)}</div>
      <div class="font-mono text-muted" style="font-size:11px; margin-top:4px;">Evidence: ${escapeHtml(r.evidence)}</div>
      <div class="font-mono" style="font-size:11px; margin-top:6px; color:var(--recon-text-primary);">
        → Action: ${escapeHtml(r.suggested_action)}
      </div>
    `;

    if (isCritical) {
      blockersContainer.appendChild(item);
    } else {
      warningsContainer.appendChild(item);
    }
  });

  // Check duplicate source assignments
  const duplicates = getDuplicateSourceAssignments();
  duplicates.forEach((targets, srcCol) => {
    if (targets.length > 1) {
      const item = document.createElement("div");
      item.className = "risk-card-item warning";
      item.innerHTML = `
        <div class="risk-card-header">
          <span class="font-mono text-amber" style="font-weight:600;">[WARN_DUPLICATE_SOURCE] Source '${escapeHtml(srcCol)}' is mapped to multiple targets</span>
          <span class="badge badge-amber">AMBIGUOUS / DUPLICATE</span>
        </div>
        <div class="text-secondary" style="font-size:12px; margin-top:4px;">
          Source column '<strong>${escapeHtml(srcCol)}</strong>' is assigned to ${targets.length} target fields: <code>${escapeHtml(targets.join(", "))}</code>.
        </div>
        <div class="font-mono" style="font-size:11px; margin-top:6px; color:var(--recon-text-primary);">
          → Verification Note: Confirm whether multiple target fields should ingest this identical source data stream.
        </div>
      `;
      warningsContainer.appendChild(item);
    }
  });

  if (blockersContainer.children.length === 0) {
    blockersContainer.innerHTML = `<div class="font-mono text-emerald" style="padding:10px 0;">✓ Zero hard blockers detected. Mapping plan is complete.</div>`;
  }
  if (warningsContainer.children.length === 0) {
    warningsContainer.innerHTML = `<div class="font-mono text-muted" style="padding:10px 0;">No quality or contract warnings detected.</div>`;
  }

  updateApprovalGateState();
}

function updateApprovalGateState() {
  if (!currentAssessment) return;
  const proposals = currentAssessment.proposals || [];
  let unmappedRequired = 0;

  proposals.forEach(p => {
    const isReq = p.required === true;
    const chosen = mappingOverrides[p.target_field] !== undefined
      ? mappingOverrides[p.target_field]
      : (p.proposed_source_field || "");
    if (isReq && !chosen) {
      unmappedRequired++;
    }
  });

  const banner = document.getElementById("radar-status-banner");
  const heading = document.getElementById("radar-status-heading");
  const sub = document.getElementById("radar-status-sub");
  const badge = document.getElementById("radar-status-badge");
  const btnApprove = document.getElementById("btn-approve");
  const dot = document.getElementById("step-audit-dot");
  const ackChecked = document.getElementById("ack-checkbox").checked;

  if (unmappedRequired > 0) {
    banner.className = "radar-status-card blocked";
    heading.textContent = `BLOCKED — ${unmappedRequired} REQUIRED FIELD${unmappedRequired > 1 ? "S" : ""} UNRESOLVED`;
    sub.textContent = "Adapter synthesis is locked until all required target fields have explicit source mappings.";
    badge.className = "badge badge-rose";
    badge.textContent = "BLOCKED";

    btnApprove.disabled = true;
    btnApprove.className = "btn btn-danger";
    btnApprove.textContent = `CANNOT APPROVE (Resolve ${unmappedRequired} Hard Blocker${unmappedRequired > 1 ? "s" : ""})`;

    dot.classList.remove("hidden");
    dot.className = "recon-step-dot blocked";
  } else {
    banner.className = "radar-status-card ready";
    heading.textContent = "READY FOR ADAPTER GENERATION";
    sub.textContent = "All required target fields are mapped. Human sign-off required to compile adapter.";
    badge.className = "badge badge-emerald";
    badge.textContent = "VERIFIED";

    dot.classList.add("hidden");

    if (ackChecked) {
      btnApprove.disabled = false;
      btnApprove.className = "btn btn-emerald";
      btnApprove.textContent = "COMMIT MAPPING PLAN & GENERATE ADAPTER →";
    } else {
      btnApprove.disabled = true;
      btnApprove.className = "btn btn-emerald";
      btnApprove.textContent = "Acknowledge Risks Above to Enable Sign-Off";
    }
  }

  updateDynamicIsland();
}

// =============================================================================
// Approval & Validation Execution (04 Audit -> 05 Adapter, 06 Validate, 07 Dossier)
// =============================================================================

async function handleApproveAndGenerate() {
  hideGlobalError();
  const btn = document.getElementById("btn-approve");
  if (!currentSessionId) {
    showGlobalError("NO ACTIVE SESSION", "Please assess a dataset before approving.", btn);
    return;
  }

  const reviewer = document.getElementById("reviewer-name-input").value.trim() || "lead_engineer";

  // Harvest overrides
  const proposals = currentAssessment.proposals || [];
  const overrides = {};
  for (const p of proposals) {
    const chosen = mappingOverrides[p.target_field] !== undefined
      ? mappingOverrides[p.target_field]
      : (p.proposed_source_field || "");
    if (p.required && !chosen) {
      showGlobalError("BLOCKER DETECTED", `Target field '${p.target_field}' is required but unmapped.`, btn);
      return;
    }
    if (chosen) {
      overrides[p.target_field] = chosen;
    }
  }

  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Synthesizing AST Adapter & Validating...";

  try {
    const res = await fetch("/api/approve-and-generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        reviewer: reviewer,
        overrides: overrides,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      if (res.status === 404) {
        showSessionLostModal();
        return;
      }
      showGlobalError("ADAPTER COMPILATION FAILED", data.detail || "Unable to compile and validate adapter.", btn);
      btn.disabled = false;
      btn.textContent = origText;
      return;
    }

    currentResults = data;

    // Render downstream screens
    renderAdapterWorkbench(data);
    renderValidationLab(data);
    renderReadinessDossier(data);

    // Audio success feedback
    SoundEngine.playSuccess();

    // Navigate to Step 05 Adapter
    navigateToStep(5);
  } catch (err) {
    showGlobalError("NETWORK ERROR", err.message, btn);
    btn.disabled = false;
    btn.textContent = origText;
  }
}

// =============================================================================
// Screen E: Adapter Code Workbench
// =============================================================================

function renderAdapterWorkbench(data) {
  const adapter = data.adapter;
  document.getElementById("adapter-artifact-title").textContent =
    `${adapter.adapter_name}.py | Contract: ${adapter.contract_name} (v${adapter.contract_version}) | Python 3.11`;

  const code = adapter.python_code || "";
  const lines = code.split("\n");

  // Line numbers gutter
  const gutter = document.getElementById("code-gutter");
  gutter.innerHTML = lines.map((_, i) => `<div>${i + 1}</div>`).join("");

  // Simple semantic syntax highlight
  const codeDisplay = document.getElementById("adapter-code-display");
  codeDisplay.innerHTML = lines.map(line => highlightPythonLine(line)).join("\n");

  // Download link
  const dlBtn = document.getElementById("btn-download-adapter-py");
  dlBtn.href = `/api/download/adapter/${data.session_id}`;
}

function highlightPythonLine(line) {
  let safe = escapeHtml(line);
  // Comments
  if (safe.trim().startsWith("#")) {
    return `<span class="syn-com">${safe}</span>`;
  }
  // Keywords
  safe = safe.replace(/\b(def|return|if|else|elif|import|from|class|try|except|for|in|is|not|and|or|None|True|False)\b/g, '<span class="syn-kw">$1</span>');
  // Strings
  safe = safe.replace(/(&quot;.*?&quot;|&#039;.*?&#039;)/g, '<span class="syn-str">$1</span>');
  return safe;
}

function handleCopyCode() {
  if (!currentResults || !currentResults.adapter) return;
  const code = currentResults.adapter.python_code;
  const btn = document.getElementById("btn-copy-code");
  const origHtml = btn.innerHTML;

  function showCopied() {
    btn.textContent = "Copied to Clipboard";
    setTimeout(() => { btn.innerHTML = origHtml; }, 1800);
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(code).then(showCopied).catch(() => {
      fallbackCopy(code, showCopied);
    });
  } else {
    fallbackCopy(code, showCopied);
  }
}

function fallbackCopy(text, onSuccess) {
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    if (onSuccess) onSuccess();
  } catch (e) {
    console.error("Clipboard copy failed:", e);
  }
}

// =============================================================================
// Screen F: Validation Lab & Swiss Precision Batch Matrix
// =============================================================================

function renderRecordMatrix(data) {
  const grid = document.getElementById("record-cells-grid");
  const countEl = document.getElementById("matrix-record-count");
  const callout = document.getElementById("record-cell-inspector");
  if (!grid) return;

  const val = (data && data.validation) ? data.validation : null;
  const total = val ? (val.total_input_records || 0) : 0;
  const quarantined = val ? (val.quarantined_records_count || 0) : 0;
  const valid = val ? (val.valid_records_count || 0) : 0;

  if (countEl) countEl.textContent = total;
  grid.innerHTML = "";

  if (!val || total === 0) {
    grid.innerHTML = `<span class="text-muted" style="font-size: 11px; padding: 4px;">Awaiting validation batch execution...</span>`;
    return;
  }

  const sampleQuar = val.sample_quarantined_records || [];
  const quarIndices = new Set(sampleQuar.map(r => r.row_index || r.record_index || 0));

  // Render record cells (up to 120 for high density performance)
  const displayLimit = Math.min(total, 120);

  for (let i = 1; i <= displayLimit; i++) {
    const isQuar = quarIndices.has(i) || (quarantined > 0 && i <= quarantined);
    const cell = document.createElement("div");
    cell.className = `record-cell ${isQuar ? "quarantined" : "valid"}`;
    cell.textContent = i;
    cell.title = `Row #${i}: ${isQuar ? "Quarantined" : "Valid"}`;

    cell.addEventListener("mouseenter", () => {
      if (callout) {
        callout.classList.remove("hidden");
        callout.innerHTML = `
          <div>
            <span style="font-weight: 700; color: ${isQuar ? "var(--recon-rose-text)" : "var(--recon-emerald-text)"};">
              ROW #${i} [${isQuar ? "QUARANTINED" : "CONFORMING"}]
            </span>
            <span class="text-muted" style="margin-left: 8px;">Target schema invariants evaluated</span>
          </div>
          <span class="badge ${isQuar ? "badge-rose" : "badge-emerald"}">${isQuar ? "Violation Detected" : "Schema Cleared"}</span>
        `;
      }
    });

    cell.addEventListener("click", () => {
      if (isQuar) {
        const qSection = document.getElementById("quarantine-tbody");
        if (qSection) {
          qSection.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    });

    grid.appendChild(cell);
  }

  if (total > displayLimit) {
    const more = document.createElement("span");
    more.className = "text-muted";
    more.style.fontSize = "10px";
    more.style.alignSelf = "center";
    more.style.padding = "0 6px";
    more.textContent = `+${total - displayLimit} more`;
    grid.appendChild(more);
  }
}

function renderValidationLab(data) {
  const val = data.validation;
  const total = val.total_input_records;
  const valid = val.valid_records_count;
  const quarantined = val.quarantined_records_count;
  const rate = val.contract_pass_rate;

  const validPct = total > 0 ? ((valid / total) * 100).toFixed(1) : "0";
  const quarnPct = total > 0 ? ((quarantined / total) * 100).toFixed(1) : "0";

  // Four Core Accounting Cards
  document.getElementById("metric-total-records").textContent = Number(total).toLocaleString();
  document.getElementById("metric-valid-records").textContent = Number(valid).toLocaleString();
  document.getElementById("metric-valid-pct").textContent = `${validPct}%`;
  document.getElementById("metric-quarantined-records").textContent = Number(quarantined).toLocaleString();
  document.getElementById("metric-quarantined-pct").textContent = `${quarnPct}%`;
  document.getElementById("metric-pass-rate").textContent = `${rate}%`;

  // Conformance Partition Meter
  const segValid = document.getElementById("meter-segment-valid");
  const segQuar = document.getElementById("meter-segment-quar");
  if (segValid) segValid.style.width = `${validPct}%`;
  if (segQuar) segQuar.style.width = `${quarnPct}%`;

  const statusBadge = document.getElementById("conformance-status-badge");
  if (statusBadge) {
    if (quarantined === 0) {
      statusBadge.className = "badge badge-emerald";
      statusBadge.textContent = "100% Conforming";
    } else {
      statusBadge.className = "badge badge-amber";
      statusBadge.textContent = `${validPct}% Pass · ${quarantined} Quarantined`;
    }
  }

  const identityTag = document.getElementById("conformance-identity-tag");
  if (identityTag) {
    identityTag.textContent = `N_total (${total}) = N_valid (${valid}) + N_quarantine (${quarantined})`;
  }

  // Render Interactive Record Cell Matrix
  renderRecordMatrix(data);

  // Ledger Accounting Identity Verification: N_total = N_valid + N_quarantine
  const isBalanced = total === (valid + quarantined);
  const ledgerBar = document.getElementById("ledger-balance-bar");
  const ledgerEq = document.getElementById("ledger-balance-equation");

  if (isBalanced) {
    if (ledgerBar) ledgerBar.className = "ledger-balance-bar balanced";
    if (ledgerBar && ledgerBar.firstElementChild) ledgerBar.firstElementChild.textContent = "[✓ LEDGER BALANCED]";
    if (ledgerEq) ledgerEq.textContent = `N_total (${total}) = N_valid (${valid}) + N_quarantine (${quarantined}). Zero data loss verified.`;
  } else {
    if (ledgerBar) ledgerBar.className = "ledger-balance-bar unbalanced";
    if (ledgerBar && ledgerBar.firstElementChild) ledgerBar.firstElementChild.textContent = "[✕ LEDGER UNBALANCED]";
    if (ledgerEq) ledgerEq.textContent = `CRITICAL INTEGRITY FAILURE: N_total (${total}) ≠ N_valid (${valid}) + N_quarantine (${quarantined}).`;
  }

  // Test Cases
  const testContainer = document.getElementById("test-cases-container");
  testContainer.innerHTML = "";
  const testBadge = document.getElementById("tests-pass-badge");

  if (val.all_tests_passed) {
    testBadge.className = "badge badge-emerald";
    testBadge.textContent = "All Tests Passed";
  } else {
    testBadge.className = "badge badge-rose";
    testBadge.textContent = "Test Failures Detected";
  }

  (val.test_case_results || []).forEach(tc => {
    const item = document.createElement("div");
    item.style.padding = "6px 0";
    item.style.borderBottom = "1px solid var(--recon-border-subtle)";
    item.style.display = "flex";
    item.style.justifyContent = "space-between";
    item.style.alignItems = "center";
    item.innerHTML = `
      <div>
        <span class="font-mono" style="font-weight:600; color:var(--recon-text-primary);">${tc.passed ? "✓" : "✕"} ${escapeHtml(tc.test_name)}</span>
        <span class="text-muted" style="font-size:11px; margin-left:8px;">Expected: ${escapeHtml(tc.expected_behavior)}</span>
      </div>
      <span class="badge ${tc.passed ? "badge-emerald" : "badge-rose"}">${tc.passed ? "PASS" : "FAIL"}</span>
    `;
    testContainer.appendChild(item);
  });

  // Quarantine Diagnostic Ledger
  const qTbody = document.getElementById("quarantine-tbody");
  const qBadge = document.getElementById("quarantine-count-badge");
  qTbody.innerHTML = "";

  if (quarantined > 0) {
    qBadge.textContent = `${quarantined} Quarantined`;
    qBadge.className = "badge badge-rose";

    (val.sample_quarantined_records || []).forEach((qr, index) => {
      const tr = document.createElement("tr");
      tr.dataset.index = index;
      tr.style.cursor = "pointer";

      const reasons = qr.failure_reasons || qr.errors || ["Schema violation"];
      tr.innerHTML = `
        <td class="font-mono text-muted">Row #${qr.row_index || qr.record_index || index}</td>
        <td class="font-mono text-rose" style="font-weight:600;">${escapeHtml(reasons[0])}</td>
        <td class="text-secondary">${escapeHtml(reasons.join("; "))}</td>
      `;

      tr.addEventListener("click", () => {
        selectQuarantineRow(index, qr);
      });

      qTbody.appendChild(tr);
    });
  } else {
    qBadge.textContent = "0 Quarantined";
    qBadge.className = "badge badge-emerald";
    qTbody.innerHTML = `<tr><td colspan="3" class="text-muted" style="text-align:center; padding:16px;">Zero records quarantined. 100% of input rows satisfied target contract schema.</td></tr>`;
  }

  updateDynamicIsland();
}

function selectQuarantineRow(index, qr) {
  selectedQuarantineIndex = index;
  const rows = document.querySelectorAll("#quarantine-tbody tr");
  rows.forEach((r, idx) => r.classList.toggle("is-selected", idx === index));

  openDrawerForQuarantine(qr);
}

// =============================================================================
// Screen G: Readiness Dossier & Certified Artifacts
// =============================================================================

function renderReadinessDossier(data) {
  const sessionId = data.session_id;
  const state = data.readiness_state.toLowerCase();
  const banner = document.getElementById("dossier-status-banner");
  const heading = document.getElementById("dossier-state-heading");
  const rationale = document.getElementById("dossier-rationale-text");
  const badge = document.getElementById("dossier-state-badge");

  const seal = document.getElementById("dossier-holographic-seal");

  if (state === "pass") {
    banner.className = "radar-status-card ready";
    heading.textContent = `READINESS: PASS (${data.validation.contract_pass_rate}% Yield)`;
    badge.className = "badge badge-emerald holographic-pill";
    badge.textContent = "CERTIFIED READY";
    if (seal) seal.classList.remove("hidden");
    SoundEngine.playCelebration();
    triggerConfettiCelebration();
  } else if (state === "needs_review") {
    banner.className = "radar-status-card warning";
    heading.textContent = `READINESS: NEEDS REVIEW (${data.validation.contract_pass_rate}% Yield)`;
    badge.className = "badge badge-amber";
    badge.textContent = "REVIEW NEEDED";
    if (seal) seal.classList.add("hidden");
  } else {
    banner.className = "radar-status-card blocked";
    heading.textContent = `READINESS: BLOCKED (${data.validation.contract_pass_rate}% Yield)`;
    badge.className = "badge badge-rose";
    badge.textContent = "BLOCKED";
    if (seal) seal.classList.add("hidden");
  }

  rationale.textContent = data.readiness_rationale;

  // Artifact downloads
  document.getElementById("art-adapter-name").textContent = `${data.adapter.adapter_name}.py`;
  document.getElementById("art-dl-adapter").href = `/api/download/adapter/${sessionId}`;
  document.getElementById("art-dl-report-md").href = `/api/download/report/${sessionId}?format=md`;
  document.getElementById("art-dl-report-json").href = `/api/download/report/${sessionId}?format=json`;

  document.getElementById("art-valid-count").textContent = `${data.validation.valid_records_count} records validated`;
  document.getElementById("art-dl-valid").href = `/api/download/valid-records/${sessionId}`;

  document.getElementById("art-quarantine-count").textContent = `${data.validation.quarantined_records_count} records quarantined`;
  document.getElementById("art-dl-quarantine").href = `/api/download/quarantine-records/${sessionId}`;

  const artDlSpec = document.getElementById("art-dl-mapping-spec");
  if (artDlSpec) {
    artDlSpec.href = `/api/download/mapping-spec/${sessionId}`;
  }

  updateDynamicIsland();
}

async function handleUploadMappingSpecInStudio(file) {
  if (!currentSessionId) {
    showGlobalError("NO ACTIVE SESSION", "Please initialize an inspection before loading a mapping specification.");
    return;
  }
  hideGlobalError();
  const formData = new FormData();
  formData.append("session_id", currentSessionId);
  formData.append("spec_file", file);

  try {
    const res = await fetch("/api/upload-mapping-spec", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      showGlobalError("SPEC IMPORT FAILED", data.detail || "Unable to import mapping specification.");
      return;
    }

    // Update active session state
    currentAssessment.proposals = data.proposals_summary;
    currentAssessment.unresolved_fields = data.unresolved_fields;
    currentAssessment.unresolved_required_fields = data.unresolved_required_fields;
    currentAssessment.has_unresolved_required = (data.unresolved_required_fields.length > 0);
    mappingOverrides = {}; // Reset manual overrides in favor of spec decisions

    // Show notification banner
    const banner = document.getElementById("mapping-spec-banner");
    const bannerText = document.getElementById("mapping-spec-banner-text");
    if (banner && bannerText) {
      banner.classList.remove("hidden");
      const matchLabel = data.validation_result.contract_match ? "Exact Contract Match" : "Contract Changed (Re-validation Required)";
      bannerText.textContent = `✓ Specification loaded: Reused ${data.validation_result.reused_count} mapping decisions (${matchLabel}). Mismatches: ${data.validation_result.mismatches.length}.`;
    }

    // Re-render mapping studio and risk radar
    renderMappingStudio(currentAssessment);
    renderRiskRadar(currentAssessment);
  } catch (err) {
    showGlobalError("NETWORK ERROR", err.message);
  }
}

async function handlePurgeSession() {
  document.getElementById("modal-reset-session").classList.add("hidden");
  if (currentSessionId) {
    try {
      await fetch(`/api/session/${currentSessionId}`, { method: "DELETE" });
    } catch (_) {
      // In-memory cleanup fallback
    }
  }

  // Reset local state
  currentSessionId = null;
  currentAssessment = null;
  currentResults = null;
  mappingOverrides = {};
  stagedSourceFile = null;
  stagedContractFile = null;

  const headerPulse = document.getElementById("header-pulse");
  if (headerPulse) headerPulse.classList.remove("active");
  const sessionDisplay = document.getElementById("session-id-display");
  if (sessionDisplay) sessionDisplay.textContent = "sess_empty";
  const contractCapsule = document.getElementById("contract-capsule");
  if (contractCapsule) contractCapsule.classList.add("hidden");

  // Reset inputs
  document.getElementById("source-file-input").value = "";
  document.getElementById("sample-dataset-select").value = "";
  document.getElementById("contract-file-input").value = "";
  document.getElementById("sample-contract-select").value = "";
  document.getElementById("contract-text-area").value = "";
  document.getElementById("source-status-text").textContent = "No source file staged.";
  document.getElementById("source-status-meta").textContent = "";
  document.getElementById("contract-status-text").textContent = "No contract schema staged.";
  document.getElementById("contract-status-meta").textContent = "";

  updatePreflightStatus();
  navigateToStep(1);
}

function showSessionLostModal() {
  const modal = document.getElementById("modal-session-lost");
  if (modal) {
    modal.classList.remove("hidden");
    const dialog = modal.querySelector(".recon-modal") || modal;
    triggerHapticFeedback(dialog);
  }
}

// =============================================================================
// Contextual Inspector Drawer Rendering
// =============================================================================

function computeTransformedValue(raw, prop) {
  if (raw === null || raw === undefined) {
    return { clean: "null", op: "NULL PASS" };
  }
  const str = String(raw);
  const t = prop.target_type;
  let clean = str;
  let op = "1:1 PASS";

  if (t === "float") {
    const stripped = str.replace(/[^0-9.-]/g, "");
    const parsed = parseFloat(stripped);
    clean = isNaN(parsed) ? str : String(parsed);
    op = str !== clean ? "STRIP & FLOAT" : "1:1 FLOAT";
  } else if (t === "integer") {
    const stripped = str.replace(/[^0-9-]/g, "");
    const parsed = parseInt(stripped, 10);
    clean = isNaN(parsed) ? str : String(parsed);
    op = str !== clean ? "STRIP & INT" : "1:1 INT";
  } else if (t === "datetime") {
    clean = str.replace(/\.\d+/, "").replace(/Z$/, "+00:00");
    op = "ISO8601";
  } else if (prop.allowed_values && prop.allowed_values.length > 0) {
    clean = str.trim().toUpperCase();
    op = "NORM ENUM";
  } else if (t === "string") {
    clean = str.trim();
    op = str !== clean ? "TRIM" : "1:1 STR";
  } else if (t === "boolean") {
    clean = ["true", "1", "yes", "y"].includes(str.toLowerCase()) ? "true" : "false";
    op = "CAST BOOL";
  }
  return { clean, op };
}

function evaluateTransformExpression(expr, val) {
  if (val === null || val === undefined) return { result: "None", ok: true };
  const strVal = String(val);
  const cleanExpr = (expr || "").trim();
  if (!cleanExpr) return { result: strVal, ok: true };

  try {
    let jsExpr = cleanExpr
      .replace(/\bval\.strip\(\)/g, "strVal.trim()")
      .replace(/\bval\.upper\(\)/g, "strVal.toUpperCase()")
      .replace(/\bval\.lower\(\)/g, "strVal.toLowerCase()")
      .replace(/\bval\.title\(\)/g, "strVal.replace(/\\b\\w/g, c => c.toUpperCase())")
      .replace(/\bfloat\(val\)/g, "parseFloat(strVal)")
      .replace(/\bint\(val\)/g, "parseInt(strVal, 10)")
      .replace(/\bround\(([^,]+),\s*(\d+)\)/g, "Number(($1).toFixed($2))")
      .replace(/\bval\b/g, "strVal");

    const fn = new Function("strVal", `return ${jsExpr};`);
    const res = fn(strVal);
    return { result: String(res), ok: true };
  } catch (err) {
    return { result: `Error: ${err.message}`, ok: false };
  }
}

function renderPlaygroundPreview(expr, sampleVals) {
  const previewBox = document.getElementById("drawer-playground-preview");
  if (!previewBox) return;

  if (!sampleVals || sampleVals.length === 0) {
    previewBox.innerHTML = `<div style="padding: 8px 10px; font-size: 11px; color: var(--recon-text-muted);">No sample values available for testing.</div>`;
    return;
  }

  let html = `
    <table style="width: 100%; border-collapse: collapse; font-size: 11px; font-family: var(--font-mono);">
      <thead>
        <tr style="background: var(--recon-bg-subtle); color: var(--recon-text-muted); border-bottom: 1px solid var(--recon-border-subtle);">
          <th style="padding: 4px 8px; text-align: left; font-size: 10px;">Raw Input</th>
          <th style="padding: 4px 8px; text-align: center; width: 18px; font-size: 10px;">→</th>
          <th style="padding: 4px 8px; text-align: left; font-size: 10px;">Computed Output</th>
        </tr>
      </thead>
      <tbody>
  `;

  sampleVals.slice(0, 4).forEach(v => {
    const raw = String(v);
    const { result, ok } = evaluateTransformExpression(expr, raw);
    html += `
      <tr style="border-bottom: 1px solid var(--recon-border-subtle);">
        <td style="padding: 4px 8px; color: var(--recon-text-secondary); max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(raw)}">${escapeHtml(raw)}</td>
        <td style="padding: 4px 8px; text-align: center; color: var(--recon-text-muted);">→</td>
        <td style="padding: 4px 8px; font-weight: 600; color: ${ok ? '#30D158' : '#FF453A'}; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(result)}">${escapeHtml(result)}</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  previewBox.innerHTML = html;
}

function initTransformPlayground() {
  const input = document.getElementById("drawer-transform-expr-input");
  if (input) {
    input.addEventListener("input", () => {
      renderPlaygroundPreview(input.value, currentPlaygroundSamples);
    });
  }

  const chips = document.querySelectorAll("#drawer-transform-chips button");
  chips.forEach(btn => {
    btn.addEventListener("click", () => {
      const expr = btn.dataset.expr;
      if (input && expr) {
        input.value = expr;
        renderPlaygroundPreview(expr, currentPlaygroundSamples);
        SoundEngine.playClick();
      }
    });
  });
}

function openDrawerForMapping(prop, openDrawer = true) {
  if (openDrawer) {
    openInspectorDrawer(true);
  }

  document.getElementById("drawer-target-field").textContent = prop.target_field;
  const badge = document.getElementById("drawer-field-badge");
  badge.textContent = prop.required ? "REQUIRED" : "OPTIONAL";
  badge.className = prop.required ? "badge badge-rose" : "badge badge-muted";

  const chosenSource = mappingOverrides[prop.target_field] !== undefined
    ? mappingOverrides[prop.target_field]
    : (prop.proposed_source_field || "");

  // Tab 1: Evidence (Structured Decision & Observed Evidence)
  const evList = document.getElementById("drawer-evidence-list");

  let decisionCardHtml = "";
  if (!chosenSource && prop.required) {
    decisionCardHtml = `
      <div class="drawer-alert-card rose">
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="badge badge-rose">CRITICAL BLOCKER</span>
          <strong style="color:var(--recon-rose-text);">Missing Required Field</strong>
        </div>
        <div style="color:var(--recon-text-secondary); font-size:11px;">
          Downstream integration requires <code>${escapeHtml(prop.target_field)}</code>. Select a source column in 03 MAP to resolve.
        </div>
      </div>
    `;
  } else if (!chosenSource && !prop.required) {
    decisionCardHtml = `
      <div class="drawer-alert-card muted">
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="badge badge-muted">OPTIONAL UNMAPPED</span>
          <span>Optional Field</span>
        </div>
        <div style="color:var(--recon-text-muted); font-size:11px;">
          No source column mapped. This field will be omitted or passed as null.
        </div>
      </div>
    `;
  } else if (mappingOverrides[prop.target_field]) {
    decisionCardHtml = `
      <div class="drawer-alert-card emerald">
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="badge badge-emerald">✓ APPROVED OVERRIDE</span>
          <strong style="color:var(--recon-emerald-text);">Human Decision Confirmed</strong>
        </div>
        <div style="color:var(--recon-text-secondary); font-size:11px;">
          Manually mapped to source column <code>${escapeHtml(chosenSource)}</code>.
        </div>
      </div>
    `;
  } else if (prop.mapping_type === "transformation_required") {
    decisionCardHtml = `
      <div class="drawer-alert-card amber">
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="badge badge-amber">TRANSFORMATION REQUIRED</span>
          <strong style="color:var(--recon-amber-text);">Type Cast / Normalization</strong>
        </div>
        <div style="color:var(--recon-text-secondary); font-size:11px;">
          Aligned to <code>${escapeHtml(chosenSource)}</code> with runtime data transformation.
        </div>
      </div>
    `;
  } else {
    decisionCardHtml = `
      <div class="drawer-alert-card indigo">
        <div style="display:flex; align-items:center; gap:6px;">
          <span class="badge badge-indigo">PROPOSED MATCH</span>
          <strong style="color:var(--recon-indigo-text);">Direct Alignment</strong>
        </div>
        <div style="color:var(--recon-text-secondary); font-size:11px;">
          Heuristic engine proposed match with source column <code>${escapeHtml(chosenSource)}</code>.
        </div>
      </div>
    `;
  }

  // Format evidence items cleanly
  let evidenceItemsHtml = "";
  if (prop.evidence && prop.evidence.length > 0) {
    evidenceItemsHtml = prop.evidence.map(e => {
      // Check if candidate list string: e.g. "No candidate column found among source headers: ['a', ...]"
      const headerListMatch = e.match(/source headers:\s*(\[[^\]]+\])/);
      if (headerListMatch) {
        const prefix = e.replace(/source headers:\s*\[[^\]]+\]/, "Source headers scanned:");
        let headersList = [];
        try {
          headersList = JSON.parse(headerListMatch[1].replace(/'/g, '"'));
        } catch (_) {
          headersList = headerListMatch[1].replace(/[\[\]']/g, "").split(",").map(s => s.trim());
        }
        const chips = headersList.map(h => `<span class="badge badge-muted font-mono" style="margin:2px 3px 2px 0;">${escapeHtml(h)}</span>`).join("");
        return `
          <div class="evidence-item-card">
            <div style="font-weight:600; color:var(--recon-text-primary); margin-bottom:6px;">${escapeHtml(prefix)}</div>
            <div style="display:flex; flex-wrap:wrap; gap:2px; max-height:140px; overflow-y:auto; padding:4px 0;">${chips}</div>
          </div>
        `;
      }

      if (e.includes("requires cast") || e.includes("Type conflict") || e.includes("enum")) {
        return `
          <div class="evidence-item-card warning">
            <div class="text-amber" style="font-weight:600; display:flex; align-items:flex-start; gap:6px;">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; color:var(--recon-amber-base); flex-shrink:0; margin-top:2px;"><path d="M8 1L1 14h14L8 1z"/><line x1="8" y1="6" x2="8" y2="9"/><circle cx="8" cy="12" r="0.75" fill="currentColor"/></svg> <span>${escapeHtml(e)}</span>
            </div>
          </div>
        `;
      }

      return `
        <div class="evidence-item-card">
          <div style="color:var(--recon-text-secondary);">${escapeHtml(e)}</div>
        </div>
      `;
    }).join("");
  } else {
    evidenceItemsHtml = `<div class="text-muted" style="font-size:11px;">No heuristic evidence attached.</div>`;
  }

  evList.innerHTML = `
    ${decisionCardHtml}
    <div style="font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:var(--recon-text-muted); margin:14px 0 8px 0;">
      Observed Engine Evidence
    </div>
    <div class="evidence-items-container">${evidenceItemsHtml}</div>
  `;

  document.getElementById("drawer-heuristic-rule").innerHTML = `
    <span class="badge badge-muted font-mono" style="font-size:11px;">${escapeHtml(prop.mapping_type || "EXACT_OR_NORMALIZED_MATCH")}</span>
  `;

  // Tab 2: Samples (Before ⟷ After Morphing Diff Inspector)
  const samplesList = document.getElementById("drawer-samples-list");
  const wipeSource = document.getElementById("morph-wipe-source");
  const wipeTarget = document.getElementById("morph-wipe-target");
  const scrubSlider = document.getElementById("diff-scrub-input");
  const scrubPct = document.getElementById("morph-scrub-pct");

  if (scrubSlider && wipeTarget && scrubPct) {
    scrubSlider.value = 50;
    scrubPct.textContent = "50%";
    wipeTarget.style.clipPath = "inset(0 0 0 50%)";
    scrubSlider.oninput = (e) => {
      const val = e.target.value;
      scrubPct.textContent = `${val}%`;
      requestAnimationFrame(() => {
        wipeTarget.style.clipPath = `inset(0 0 0 ${val}%)`;
      });
    };
  }

  if (chosenSource && currentAssessment && currentAssessment.source) {
    let sampleVals = [];
    if (currentAssessment.source.columns_profile && currentAssessment.source.columns_profile[chosenSource]) {
      sampleVals = currentAssessment.source.columns_profile[chosenSource].sample_values || [];
    }
    if (sampleVals.length === 0 && currentAssessment.source.sample_rows) {
      sampleVals = currentAssessment.source.sample_rows.map(r => r[chosenSource]).filter(v => v !== undefined && v !== null);
    }
    currentPlaygroundSamples = sampleVals;

    const firstRaw = sampleVals.length > 0 ? String(sampleVals[0]) : "null";
    const { clean: firstClean } = computeTransformedValue(firstRaw, prop);

    if (wipeSource) {
      wipeSource.innerHTML = `<span><strong style="color:var(--recon-text-muted);">SOURCE:</strong> ${escapeHtml(firstRaw)}</span>`;
    }
    if (wipeTarget) {
      wipeTarget.innerHTML = `<span><strong style="color:#30D158;">TARGET:</strong> ${escapeHtml(firstClean)}</span>`;
    }

    if (sampleVals.length > 0) {
      samplesList.innerHTML = sampleVals.slice(0, 4).map(v => {
        const rawStr = String(v);
        const { clean, op } = computeTransformedValue(rawStr, prop);
        return `
          <div class="morph-sample-card">
            <div class="morph-card-flow">
              <div class="morph-cell">
                <span class="morph-cell-label">Source (${escapeHtml(chosenSource)})</span>
                <span class="morph-cell-value source" title="${escapeHtml(rawStr)}">${escapeHtml(rawStr)}</span>
              </div>
              <div class="morph-arrow">
                <span style="font-size:11px; color:var(--recon-text-muted);">→</span>
                <span class="morph-arrow-op">${escapeHtml(op)}</span>
              </div>
              <div class="morph-cell">
                <span class="morph-cell-label">Target (${escapeHtml(prop.target_type)})</span>
                <span class="morph-cell-value target" title="${escapeHtml(clean)}">${escapeHtml(clean)}</span>
              </div>
            </div>
          </div>
        `;
      }).join("");
    } else {
      samplesList.innerHTML = `<span class="text-muted font-mono" style="font-size:11px;">No non-null sample rows observed.</span>`;
    }

    const colProf = currentAssessment.source.columns_profile ? currentAssessment.source.columns_profile[chosenSource] : null;
    if (colProf) {
      document.getElementById("drawer-cardinality-meta").innerHTML =
        `Source: <code>${escapeHtml(chosenSource)}</code> | Type: <strong>${colProf.inferred_type}</strong> | Distinct: ${colProf.distinct_count} | Nulls: ${colProf.null_count} (${colProf.null_percentage}%)`;
    } else {
      document.getElementById("drawer-cardinality-meta").textContent = `Source: ${chosenSource}`;
    }
  } else {
    if (wipeSource) wipeSource.innerHTML = `<span><strong style="color:var(--recon-text-muted);">SOURCE:</strong> [UNMAPPED]</span>`;
    if (wipeTarget) wipeTarget.innerHTML = `<span><strong style="color:var(--recon-rose-text);">TARGET:</strong> ${prop.required ? 'MISSING REQUIRED' : 'OPTIONAL'}</span>`;
    samplesList.innerHTML = `<span class="text-muted font-mono" style="font-size:11px;">No source field mapped to sample.</span>`;
    document.getElementById("drawer-cardinality-meta").textContent = "";
  }

  // Tab 3: AST Transform Formula & Live Expression Playground
  const astCode = document.getElementById("drawer-ast-code");
  let defaultExpr = "val.strip()";
  if (chosenSource) {
    if (prop.target_type === "float") {
      astCode.textContent = `output['${prop.target_field}'] = float(source['${chosenSource}']) if source.get('${chosenSource}') not in (None, '') else None`;
      defaultExpr = "float(val)";
    } else if (prop.target_type === "integer") {
      astCode.textContent = `output['${prop.target_field}'] = int(source['${chosenSource}']) if source.get('${chosenSource}') not in (None, '') else None`;
      defaultExpr = "int(val)";
    } else if (prop.target_type === "datetime") {
      astCode.textContent = `output['${prop.target_field}'] = parse_iso_datetime(source['${chosenSource}'])`;
      defaultExpr = "val.strip()";
    } else if (prop.allowed_values && prop.allowed_values.length > 0) {
      astCode.textContent = `output['${prop.target_field}'] = str(source['${chosenSource}']).strip().upper()`;
      defaultExpr = "val.strip().upper()";
    } else {
      astCode.textContent = `output['${prop.target_field}'] = str(source['${chosenSource}']).strip() if source.get('${chosenSource}') is not None else None`;
      defaultExpr = "val.strip()";
    }
  } else {
    astCode.textContent = `# Field '${prop.target_field}' unmapped. No transform emitted.\n# Validation will enforce required=True and non-null constraints.`;
    defaultExpr = "val";
    currentPlaygroundSamples = [];
  }

  const exprInput = document.getElementById("drawer-transform-expr-input");
  if (exprInput) {
    exprInput.value = defaultExpr;
    renderPlaygroundPreview(defaultExpr, currentPlaygroundSamples);
  }

  // Tab 4: Schema Meta
  const metaBox = document.getElementById("drawer-schema-meta");
  metaBox.innerHTML = `
    <div style="background-color:var(--recon-bg-surface); border:1px solid var(--recon-border-subtle); border-radius:var(--radius-sm); padding:12px; display:flex; flex-direction:column; gap:6px;">
      <div>Target Field: <strong class="text-primary">${escapeHtml(prop.target_field)}</strong></div>
      <div>Expected Type: <span class="badge badge-type">${escapeHtml(prop.target_type)}</span></div>
      <div>Required: <strong class="${prop.required ? 'text-rose' : 'text-muted'}">${prop.required}</strong></div>
      <div>Nullable: <strong>${prop.nullable !== undefined ? prop.nullable : false}</strong></div>
      ${prop.allowed_values ? `<div>Allowed Values: <code>${escapeHtml(JSON.stringify(prop.allowed_values))}</code></div>` : ""}
      ${prop.pattern ? `<div>Pattern Regex: <code>/${escapeHtml(prop.pattern)}/</code></div>` : ""}
    </div>
    <div style="margin-top:10px; padding:0 4px; color:var(--recon-text-secondary); line-height:1.5;">${escapeHtml(prop.description || "No contract field description.")}</div>
  `;
}

function openDrawerForColumn(colName, colInfo, openDrawer = true) {
  if (openDrawer) {
    openInspectorDrawer(true);
  }

  document.getElementById("drawer-target-field").textContent = colName;
  const badge = document.getElementById("drawer-field-badge");
  badge.textContent = `SOURCE: ${colInfo.inferred_type.toUpperCase()}`;
  badge.className = "badge badge-indigo";

  // Tab 1: Evidence
  document.getElementById("drawer-evidence-list").innerHTML = `
    <div>Column Name: <code>${escapeHtml(colName)}</code></div>
    <div>Inferred Data Type: <strong>${colInfo.inferred_type}</strong></div>
    <div>Null Percentage: <strong>${colInfo.null_percentage}%</strong></div>
    <div>Distinct Cardinality: <strong>${colInfo.distinct_count}</strong></div>
  `;
  document.getElementById("drawer-heuristic-rule").textContent = "Deterministic Type & Nullity Profiler";

  // Tab 2: Samples
  const samplesList = document.getElementById("drawer-samples-list");
  samplesList.innerHTML = (colInfo.sample_values || []).map(v =>
    `<span class="badge badge-muted font-mono" style="margin:2px 4px 2px 0;">${escapeHtml(String(v))}</span>`
  ).join("");
  document.getElementById("drawer-cardinality-meta").innerHTML =
    `Null count: ${colInfo.null_count} | Distinct values: ${colInfo.distinct_count}`;

  // Tab 3: AST
  document.getElementById("drawer-ast-code").textContent = `source['${colName}']`;

  // Tab 4: Meta
  document.getElementById("drawer-schema-meta").innerHTML = `
    <div>Profile Source Column: <strong>${escapeHtml(colName)}</strong></div>
    <div>Detected Null Count: ${colInfo.null_count}</div>
    <div>Distinct Cardinality: ${colInfo.distinct_count}</div>
  `;
}

function openDrawerForQuarantine(qr) {
  const drawer = document.getElementById("contextual-drawer");
  drawer.classList.remove("collapsed");

  document.getElementById("drawer-target-field").textContent = `Row #${qr.row_index || qr.record_index}`;
  const badge = document.getElementById("drawer-field-badge");
  badge.textContent = "QUARANTINED";
  badge.className = "badge badge-rose";

  // Tab 1: Evidence / Diagnostic
  const reasons = qr.failure_reasons || qr.errors || [];
  document.getElementById("drawer-evidence-list").innerHTML = reasons.map(r =>
    `<div class="text-rose font-mono">• ${escapeHtml(r)}</div>`
  ).join("");
  document.getElementById("drawer-heuristic-rule").textContent = "Contract Violation & Isolation Rule";

  // Tab 2: Samples / Raw Record
  document.getElementById("drawer-samples-list").innerHTML = `
    <pre class="font-mono" style="font-size:11px; background:var(--recon-bg-root); padding:8px; border-radius:4px; max-height:160px; overflow:auto;">${escapeHtml(JSON.stringify(qr.raw_record || {}, null, 2))}</pre>
  `;
  document.getElementById("drawer-cardinality-meta").textContent = "Raw record isolated without data loss.";

  // Tab 3: AST
  document.getElementById("drawer-ast-code").textContent = `# Record failed target validation. Quarantine routing invoked.`;

  // Tab 4: Meta
  document.getElementById("drawer-schema-meta").innerHTML = `
    <div style="color:var(--recon-text-primary);">Upstream Remediation:</div>
    <div class="text-secondary" style="margin-top:4px;">
      Examine raw values above against target schema constraints. Provide source fallback or relax nullable constraints.
    </div>
  `;
}

// =============================================================================
// Keyboard Navigation & Ergonomics
// =============================================================================

function bindKeyboardNavigation() {
  document.addEventListener("keydown", e => {
    try {
      // Command Palette (⌘K / Ctrl+K) works everywhere including inputs
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        toggleCommandPalette();
        return;
      }

      // If typing in input, ignore shortcuts except Esc
      const activeTag = document.activeElement ? document.activeElement.tagName : "";
      if (["INPUT", "TEXTAREA", "SELECT"].includes(activeTag) && e.key !== "Escape") {
        return;
      }

      if (e.key === "Escape") {
        const paletteModal = document.getElementById("modal-command-palette");
        if (paletteModal && !paletteModal.classList.contains("hidden")) {
          closeCommandPalette();
          return;
        }
        closeInspectorDrawer(true);
        const modalShortcuts = document.getElementById("modal-shortcuts");
        if (modalShortcuts) modalShortcuts.classList.add("hidden");
        const modalReset = document.getElementById("modal-reset-session");
        if (modalReset) modalReset.classList.add("hidden");
        closeGuide();
        closeTour();
        const island = document.getElementById("recon-dynamic-island");
        const tray = document.getElementById("island-expanded-tray");
        if (island && tray && island.classList.contains("expanded")) {
          island.classList.remove("expanded");
          tray.classList.add("hidden");
        }
        return;
      }

      // Shortcuts modal (? or /)
      if (e.key === "?" || (e.shiftKey && e.key === "/")) {
        e.preventDefault();
        toggleShortcutsModal();
        return;
      }

      // Guide (G / g)
      if ((e.key === "g" || e.key === "G") && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        toggleGuideModal();
        return;
      }

      // Inspector (I / i)
      if ((e.key === "i" || e.key === "I") && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        toggleInspectorDrawerPin();
        return;
      }

      // Guide Modal Arrow Navigation
      const modalGuide = document.getElementById("modal-guide");
      if (modalGuide && !modalGuide.classList.contains("hidden")) {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          navigateGuideStep(-1);
          return;
        }
        if (e.key === "ArrowRight") {
          e.preventDefault();
          navigateGuideStep(1);
          return;
        }
      }

      // Floating Spotlight Tour Arrow Navigation
      const tourCard = document.getElementById("recon-guide-floating-card");
      if (tourCard && !tourCard.classList.contains("hidden")) {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          stepFloatingTour(-1);
          return;
        }
        if (e.key === "ArrowRight") {
          e.preventDefault();
          stepFloatingTour(1);
          return;
        }
      }

      // Step navigation: 1..7 (with Ctrl, Cmd, Alt, or standalone outside inputs)
      if (["1", "2", "3", "4", "5", "6", "7"].includes(e.key)) {
        const targetStep = parseInt(e.key, 10);
        if (isStepAvailable(targetStep)) {
          e.preventDefault();
          navigateToStep(targetStep);
        }
        return;
      }

    // Ctrl+Enter or Cmd+Enter: Advance workflow
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (currentStep === 1) {
        const btnAssess = document.getElementById("btn-assess");
        if (!btnAssess.disabled) btnAssess.click();
      } else if (currentStep === 4) {
        const btnApprove = document.getElementById("btn-approve");
        if (!btnApprove.disabled) btnApprove.click();
      } else if (currentStep < 7) {
        navigateToStep(currentStep + 1);
      }
      return;
    }

    // Enter without modifiers: Open Contextual Inspector for active selection
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      if (currentStep === 2) {
        const rows = document.querySelectorAll("#profile-tbody tr");
        if (rows[selectedProfileIndex]) {
          e.preventDefault();
          rows[selectedProfileIndex].click();
        }
      } else if (currentStep === 3) {
        const rows = Array.from(document.querySelectorAll("#mappings-tbody tr:not(.hidden)"));
        if (rows[selectedMappingIndex]) {
          e.preventDefault();
          rows[selectedMappingIndex].click();
        }
      } else if (currentStep === 6) {
        const rows = document.querySelectorAll("#quarantine-tbody tr");
        if (rows[selectedQuarantineIndex]) {
          e.preventDefault();
          rows[selectedQuarantineIndex].click();
        }
      }
      return;
    }

    // Space: Toggle contextual inspector drawer
    if (e.key === " " && !["INPUT", "TEXTAREA", "SELECT"].includes(activeTag)) {
      e.preventDefault();
      toggleInspectorDrawerPin();
      SoundEngine.playClick();
      return;
    }

    // Audio Mute Toggle: M / m
    if ((e.key === "m" || e.key === "M") && !e.ctrlKey && !e.metaKey && !["INPUT", "TEXTAREA", "SELECT"].includes(activeTag)) {
      e.preventDefault();
      SoundEngine.toggleMute();
      return;
    }

    // Table row navigation: J / K or Down / Up
    if (currentStep === 2) {
      // Screen B: Profile Matrix
      const rows = document.querySelectorAll("#profile-tbody tr");
      if (rows.length === 0) return;
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        selectedProfileIndex = Math.min(rows.length - 1, selectedProfileIndex + 1);
        rows[selectedProfileIndex].click();
        rows[selectedProfileIndex].scrollIntoView({ block: "nearest" });
        SoundEngine.playClick();
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        selectedProfileIndex = Math.max(0, selectedProfileIndex - 1);
        rows[selectedProfileIndex].click();
        rows[selectedProfileIndex].scrollIntoView({ block: "nearest" });
        SoundEngine.playClick();
      }
    } else if (currentStep === 3) {
      // Screen C: Mapping Studio
      const rows = Array.from(document.querySelectorAll("#mappings-tbody tr:not(.hidden)"));
      if (rows.length === 0) return;
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        selectedMappingIndex = Math.min(rows.length - 1, selectedMappingIndex + 1);
        rows[selectedMappingIndex].click();
        rows[selectedMappingIndex].scrollIntoView({ block: "nearest" });
        SoundEngine.playClick();
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        selectedMappingIndex = Math.max(0, selectedMappingIndex - 1);
        rows[selectedMappingIndex].click();
        rows[selectedMappingIndex].scrollIntoView({ block: "nearest" });
        SoundEngine.playClick();
      }
    } else if (currentStep === 6) {
      // Screen F: Quarantine Ledger
      const rows = document.querySelectorAll("#quarantine-tbody tr");
      if (rows.length === 0) return;
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        selectedQuarantineIndex = Math.min(rows.length - 1, selectedQuarantineIndex + 1);
        rows[selectedQuarantineIndex].click();
        rows[selectedQuarantineIndex].scrollIntoView({ block: "nearest" });
        SoundEngine.playClick();
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        selectedQuarantineIndex = Math.max(0, selectedQuarantineIndex - 1);
        rows[selectedQuarantineIndex].click();
        rows[selectedQuarantineIndex].scrollIntoView({ block: "nearest" });
        SoundEngine.playClick();
      }
    }
  } catch (err) {
    console.warn("[Recon] Keyboard navigation event error:", err);
  }
});
}

// =============================================================================
// Command Palette Engine (⌘K / Ctrl+K) — Apple-Grade Dev Navigation
// =============================================================================

let paletteSelectedIdx = 0;
let paletteCurrentItems = [];

function initCommandPalette() {
  const btnCmd = document.getElementById("btn-command-palette");
  if (btnCmd) {
    btnCmd.addEventListener("click", () => openCommandPalette());
  }

  const btnClose = document.getElementById("btn-close-palette");
  if (btnClose) {
    btnClose.addEventListener("click", () => closeCommandPalette());
  }

  const modalPalette = document.getElementById("modal-command-palette");
  if (modalPalette) {
    modalPalette.addEventListener("click", e => {
      if (e.target === modalPalette) {
        closeCommandPalette();
      }
    });
  }

  const input = document.getElementById("palette-search-input");
  if (input) {
    input.addEventListener("input", e => {
      renderPaletteResults(e.target.value);
    });
    input.addEventListener("keydown", handlePaletteKeydown);
  }
}

function openCommandPalette() {
  const modal = document.getElementById("modal-command-palette");
  const input = document.getElementById("palette-search-input");
  if (!modal || !input) return;

  modal.classList.remove("hidden");
  input.value = "";
  paletteSelectedIdx = 0;
  renderPaletteResults("");
  setTimeout(() => input.focus(), 50);
}

function closeCommandPalette() {
  const modal = document.getElementById("modal-command-palette");
  if (modal) {
    modal.classList.add("hidden");
  }
}

function toggleCommandPalette() {
  const modal = document.getElementById("modal-command-palette");
  if (!modal) return;
  if (modal.classList.contains("hidden")) {
    openCommandPalette();
  } else {
    closeCommandPalette();
  }
}

function handlePaletteKeydown(e) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (paletteCurrentItems.length > 0) {
      paletteSelectedIdx = (paletteSelectedIdx + 1) % paletteCurrentItems.length;
      updatePaletteSelection();
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (paletteCurrentItems.length > 0) {
      paletteSelectedIdx = (paletteSelectedIdx - 1 + paletteCurrentItems.length) % paletteCurrentItems.length;
      updatePaletteSelection();
    }
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (paletteCurrentItems[paletteSelectedIdx]) {
      executePaletteItem(paletteCurrentItems[paletteSelectedIdx]);
    }
  } else if (e.key === "Escape") {
    e.preventDefault();
    closeCommandPalette();
  }
}

function executePaletteItem(item) {
  if (!item) return;
  if (item.disabled) {
    const dialog = document.querySelector("#modal-command-palette .recon-palette-dialog") || document.getElementById("modal-command-palette");
    triggerHapticFeedback(dialog);
    return;
  }
  closeCommandPalette();
  if (typeof item.action === "function") {
    item.action();
  }
}

function updatePaletteSelection() {
  const itemEls = document.querySelectorAll("#palette-results-list .recon-palette-item");
  itemEls.forEach((el, idx) => {
    const isSel = idx === paletteSelectedIdx;
    el.classList.toggle("selected", isSel);
    if (isSel) {
      el.scrollIntoView({ block: "nearest" });
    }
  });
}

function renderPaletteResults(query) {
  const listContainer = document.getElementById("palette-results-list");
  if (!listContainer) return;

  const allItems = [];

  // Reusable micro-icon SVGs
  const svgIcons = {
    demo: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4l6-3 6 3-6 3-6-3z"/><path d="M2 4v8l6 3 6-3V4"/><path d="M8 7v8"/></svg>`,
    action: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="9 1 3 9 8 9 7 15 13 7 8 7"/></svg>`,
    code: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 4 1 8 5 12"/><polyline points="11 4 15 8 11 12"/><line x1="10" y1="2" x2="6" y2="14"/></svg>`,
    shield: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 1L2 4v4c0 4.5 4.5 7 6 7s6-2.5 6-7V4L8 1z"/></svg>`,
    doc: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2h7l4 4v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/><path d="M10 2v4h4"/></svg>`,
    spec: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="4" x2="13" y2="4"/><circle cx="6" cy="4" r="1.5" fill="currentColor"/><line x1="3" y1="8" x2="13" y2="8"/><circle cx="10" cy="8" r="1.5" fill="currentColor"/><line x1="3" y1="12" x2="13" y2="12"/><circle cx="5" cy="12" r="1.5" fill="currentColor"/></svg>`,
    inspector: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>`,
    guide: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><polygon points="8,4.5 9.5,8 8,11.5 6.5,8" fill="currentColor"/></svg>`,
    theme: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M8 2a6 6 0 0 1 0 12V2z" fill="currentColor"/></svg>`,
    trash: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h10M6 4V2h4v2M5 4v9a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1V4"/></svg>`,
    check: `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="2 8 6 12 14 4"/></svg>`,
    lock: `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="10" height="7" rx="1.5"/><path d="M5 7V5a3 3 0 0 1 6 0v2"/></svg>`,
    target: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><circle cx="8" cy="8" r="2" fill="currentColor"/></svg>`,
    column: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="12" height="10" rx="1"/><line x1="6" y1="3" x2="6" y2="13"/><line x1="10" y1="3" x2="10" y2="13"/></svg>`
  };

  // 1. Actions
  allItems.push({
    id: "load-b2b",
    category: "Quick Actions",
    icon: svgIcons.demo,
    title: "Load Pilot Benchmark (B2B Vendor Invoices)",
    sub: "Gate 09 Real-World Dataset",
    shortcut: "Demo",
    action: () => handleQuickDemoLoad()
  });

  allItems.push({
    id: "load-indian-voicemail",
    category: "Quick Actions",
    icon: svgIcons.demo,
    title: "Load Indian AI Voicemail Scenario",
    sub: "Conversational Telephony, Indic STT & Voicemail Ingestion",
    shortcut: "India",
    action: () => loadScenario("indian_voicemail")
  });

  allItems.push({
    id: "run-preflight",
    category: "Quick Actions",
    icon: svgIcons.action,
    title: "Run Preflight Ingestion & Profiler",
    sub: "Assess staged source & schema",
    shortcut: "Enter",
    action: () => {
      const btn = document.getElementById("btn-assess");
      if (btn && !btn.disabled) btn.click();
    }
  });

  if (currentAssessment) {
    allItems.push({
      id: "generate-adapter",
      category: "Quick Actions",
      icon: svgIcons.code,
      title: "Generate Python Adapter (adapter.py)",
      sub: "Approve mapping spec & build code",
      shortcut: "Adapter",
      action: () => {
        navigateToStep(3);
        const ack = document.getElementById("ack-checkbox");
        if (ack) {
          ack.checked = true;
          updateApprovalGateState();
        }
        handleApproveAndGenerate();
      }
    });

    allItems.push({
      id: "run-quarantine",
      category: "Quick Actions",
      icon: svgIcons.shield,
      title: "Execute Quarantine Validation Engine",
      sub: "Run in-process sandbox tests",
      shortcut: "Validate",
      action: () => {
        if (isStepAvailable(6)) {
          navigateToStep(6);
          const btn = document.getElementById("btn-validate-run");
          if (btn) btn.click();
        }
      }
    });

    allItems.push({
      id: "download-report",
      category: "Quick Actions",
      icon: svgIcons.doc,
      title: "Download Readiness Dossier (Markdown)",
      sub: "Certified preflight audit report",
      shortcut: "Download",
      action: () => {
        const btn = document.getElementById("btn-download-report-md");
        if (btn) btn.click();
      }
    });

    allItems.push({
      id: "download-spec",
      category: "Quick Actions",
      icon: svgIcons.spec,
      title: "Export Reusable Mapping Spec (JSON)",
      sub: "recon_mapping_spec.json for CI/CD",
      shortcut: "Spec",
      action: () => {
        const btn = document.getElementById("btn-download-spec-json");
        if (btn) btn.click();
      }
    });
  }

  allItems.push({
    id: "toggle-inspector",
    category: "Interface & Tools",
    icon: svgIcons.inspector,
    title: "Toggle Contextual Inspector",
    sub: "Drawer with AST, samples & radar",
    shortcut: "I",
    action: () => toggleInspectorDrawerPin()
  });

  allItems.push({
    id: "toggle-guide",
    category: "Interface & Tools",
    icon: svgIcons.guide,
    title: "Toggle Interactive Guide & Tour",
    sub: "Walkthrough of 7-step pipeline",
    shortcut: "G",
    action: () => toggleGuideModal()
  });

  allItems.push({
    id: "toggle-theme",
    category: "Interface & Tools",
    icon: svgIcons.theme,
    title: "Toggle Theme (Dark / Light)",
    sub: "Switch visual appearance",
    action: () => {
      const themeBtn = document.getElementById("btn-theme-toggle");
      if (themeBtn) themeBtn.click();
    }
  });

  allItems.push({
    id: "toggle-sound",
    category: "Interface & Tools",
    icon: svgIcons.theme,
    title: "Toggle Audio Synthesizer Feedback",
    sub: isAudioMuted ? "Currently Muted — Unmute click & chimes" : "Currently Active — Mute audio feedback",
    shortcut: "M",
    action: () => {
      SoundEngine.toggleMute();
    }
  });

  allItems.push({
    id: "reset-session",
    category: "Interface & Tools",
    icon: svgIcons.trash,
    title: "Reset Session & Purge Sandbox",
    sub: "Safely wipe in-memory data",
    action: () => {
      const resetBtn = document.getElementById("btn-reset-session");
      if (resetBtn) resetBtn.click();
    }
  });

  // 2. Workflow Navigation (01 - 07)
  const steps = [
    { num: 1, name: "01 Ingest", desc: "Source files & target contracts" },
    { num: 2, name: "02 Profile", desc: "Data profile & type inference matrix" },
    { num: 3, name: "03 Map", desc: "Mapping Studio & interactive Flow Graph" },
    { num: 4, name: "04 Audit", desc: "Risk Radar & confidence diagnostics" },
    { num: 5, name: "05 Adapter", desc: "Generated Python code workbench" },
    { num: 6, name: "06 Validate", desc: "Quarantine Ledger & yield accounting" },
    { num: 7, name: "07 Dossier", desc: "Readiness certification & downloads" }
  ];

  steps.forEach(s => {
    const avail = isStepAvailable(s.num);
    allItems.push({
      id: `step-${s.num}`,
      category: "Workflow Navigation",
      icon: avail ? svgIcons.check : svgIcons.lock,
      title: s.name,
      sub: s.desc + (avail ? "" : " (Locked)"),
      shortcut: `Ctrl+${s.num}`,
      disabled: !avail,
      action: () => {
        if (isStepAvailable(s.num)) {
          navigateToStep(s.num);
        }
      }
    });
  });

  // 3. Live Target Schema Fields
  if (currentAssessment && currentAssessment.proposals) {
    currentAssessment.proposals.forEach((prop, idx) => {
      const isReq = prop.target_required || prop.required;
      allItems.push({
        id: `target-field-${prop.target_field}`,
        category: "Target Schema Fields",
        icon: svgIcons.target,
        title: prop.target_field,
        sub: `Type: ${prop.target_type || "string"} • ${isReq ? "Required" : "Optional"} • Source: ${prop.source_column || "[Unmapped]"}`,
        shortcut: "Map",
        action: () => {
          navigateToStep(3);
          selectMappingRow(idx, prop, true);
          setTimeout(() => {
            const tr = document.querySelector(`#mappings-tbody tr[data-target="${prop.target_field}"]`);
            if (tr) tr.scrollIntoView({ behavior: "smooth", block: "center" });
          }, 80);
        }
      });
    });
  }

  // 4. Live Source Dataset Columns
  if (currentAssessment && currentAssessment.source && currentAssessment.source.columns) {
    const profile = currentAssessment.source;
    profile.columns.forEach((colName, idx) => {
      const colInfo = profile.columns_profile ? profile.columns_profile[colName] : {};
      allItems.push({
        id: `source-col-${colName}`,
        category: "Source Dataset Columns",
        icon: svgIcons.column,
        title: colName,
        sub: `Inferred: ${colInfo.inferred_type || "unknown"} • Nulls: ${colInfo.null_count || 0}`,
        shortcut: "Profile",
        action: () => {
          navigateToStep(2);
          selectProfileRow(idx, colName, colInfo, true);
          setTimeout(() => {
            const tr = document.querySelector(`#profile-tbody tr[data-column="${colName}"]`);
            if (tr) tr.scrollIntoView({ behavior: "smooth", block: "center" });
          }, 80);
        }
      });
    });
  }

  // Filter
  const q = (query || "").trim().toLowerCase();
  paletteCurrentItems = q === "" ? allItems : allItems.filter(item => {
    return item.title.toLowerCase().includes(q) ||
           item.category.toLowerCase().includes(q) ||
           (item.sub && item.sub.toLowerCase().includes(q));
  });

  // Clamp selection
  if (paletteSelectedIdx >= paletteCurrentItems.length) {
    paletteSelectedIdx = 0;
  }

  if (paletteCurrentItems.length === 0) {
    listContainer.innerHTML = `<div class="recon-palette-empty">No matching actions, steps, or fields found for "${escapeHtml(query)}"</div>`;
    return;
  }

  // Render grouped by category
  let html = "";
  let currentGroup = "";
  paletteCurrentItems.forEach((item, idx) => {
    if (item.category !== currentGroup) {
      currentGroup = item.category;
      html += `<div class="recon-palette-group-title">${escapeHtml(currentGroup)}</div>`;
    }
    const isSelected = idx === paletteSelectedIdx;
    html += `
      <div class="recon-palette-item ${isSelected ? "selected" : ""}" data-idx="${idx}" role="option" aria-selected="${isSelected}">
        <div class="recon-palette-item-left">
          <span class="recon-palette-item-icon">${item.icon}</span>
          <span class="recon-palette-item-label">${escapeHtml(item.title)}</span>
          ${item.sub ? `<span class="recon-palette-item-sub">${escapeHtml(item.sub)}</span>` : ""}
        </div>
        <div class="recon-palette-item-right">
          ${item.shortcut ? `<kbd>${escapeHtml(item.shortcut)}</kbd>` : ""}
        </div>
      </div>
    `;
  });

  listContainer.innerHTML = html;

  // Click listener
  const itemEls = listContainer.querySelectorAll(".recon-palette-item");
  itemEls.forEach(el => {
    el.addEventListener("click", () => {
      const idx = parseInt(el.dataset.idx, 10);
      if (!isNaN(idx) && paletteCurrentItems[idx]) {
        executePaletteItem(paletteCurrentItems[idx]);
      }
    });
    el.addEventListener("mouseenter", () => {
      const idx = parseInt(el.dataset.idx, 10);
      if (!isNaN(idx)) {
        paletteSelectedIdx = idx;
        updatePaletteSelection();
      }
    });
  });
}

// =============================================================================
// Feature 3: Floating Dynamic Health Island (Apple macOS / VisionOS Controller)
// =============================================================================

function initDynamicIsland() {
  const island = document.getElementById("recon-dynamic-island");
  const pill = document.getElementById("island-pill-trigger");
  const tray = document.getElementById("island-expanded-tray");
  const primaryBtn = document.getElementById("island-primary-action");
  const trayPrimaryBtn = document.getElementById("island-btn-tray-primary");
  const stepJumpBtn = document.getElementById("island-btn-step-jump");

  if (!island || !pill || !tray) return;

  // Toggle expanded tray on pill click
  pill.addEventListener("click", (e) => {
    if (e.target.closest("#island-primary-action")) return;
    const isExpanded = island.classList.toggle("expanded");
    tray.classList.toggle("hidden", !isExpanded);
  });

  // Primary quick action execution
  if (primaryBtn) {
    primaryBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      executeDynamicIslandAction();
    });
  }

  if (trayPrimaryBtn) {
    trayPrimaryBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      executeDynamicIslandAction();
    });
  }

  // Jump to step button
  if (stepJumpBtn) {
    stepJumpBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      island.classList.remove("expanded");
      tray.classList.add("hidden");
      if (typeof openCommandPalette === "function") {
        openCommandPalette();
        const searchInput = document.getElementById("palette-search-input");
        if (searchInput) {
          searchInput.value = "step";
          searchInput.dispatchEvent(new Event("input"));
        }
      } else {
        let next = currentStep + 1;
        if (next > 7 || !isStepAvailable(next)) next = 1;
        navigateToStep(next);
      }
    });
  }

  // Click outside to collapse
  document.addEventListener("click", (e) => {
    if (!island.contains(e.target) && island.classList.contains("expanded")) {
      island.classList.remove("expanded");
      tray.classList.add("hidden");
    }
  });

  // Escape key to close
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && island.classList.contains("expanded")) {
      island.classList.remove("expanded");
      tray.classList.add("hidden");
    }
  });

  updateDynamicIsland();
}

function executeDynamicIslandAction() {
  switch (currentStep) {
    case 1:
      handleAssessIntegration();
      break;
    case 2:
      navigateToStep(3);
      break;
    case 3:
      navigateToStep(4);
      break;
    case 4: {
      const ack = document.getElementById("ack-checkbox");
      if (ack && !ack.checked) {
        ack.checked = true;
        updateApprovalGateState();
      }
      handleApproveAndGenerate();
      break;
    }
    case 5:
      navigateToStep(6);
      break;
    case 6:
      navigateToStep(7);
      break;
    case 7: {
      const dlBtn = document.getElementById("art-dl-report-md");
      if (dlBtn && dlBtn.href) {
        window.location.href = dlBtn.href;
      }
      break;
    }
  }
}

function updateDynamicIsland() {
  const island = document.getElementById("recon-dynamic-island");
  if (!island) return;

  const dot = document.getElementById("island-status-dot");
  const title = document.getElementById("island-status-title");
  const metric = document.getElementById("island-metric-text");
  const btn = document.getElementById("island-primary-action");
  const btnIcon = document.getElementById("island-btn-icon");
  const btnText = document.getElementById("island-btn-text");

  // Tray elements
  const trayStepBadge = document.getElementById("island-tray-step-badge");
  const trayYield = document.getElementById("island-tray-yield");
  const trayMapped = document.getElementById("island-tray-mapped");
  const trayRisks = document.getElementById("island-tray-risks");
  const trayQuarantine = document.getElementById("island-tray-quarantine");
  const trayPrimaryBtn = document.getElementById("island-btn-tray-primary");

  const stepNames = {
    1: "Ingest",
    2: "Profile",
    3: "Map",
    4: "Audit",
    5: "Adapter",
    6: "Validate",
    7: "Dossier"
  };

  if (trayStepBadge) {
    trayStepBadge.textContent = `Step 0${currentStep} / ${stepNames[currentStep] || "Workflow"}`;
  }

  // Compute stats from currentAssessment
  let totalProposals = 0;
  let mappedCount = 0;
  let unmappedReq = 0;
  if (currentAssessment && currentAssessment.proposals) {
    totalProposals = currentAssessment.proposals.length;
    currentAssessment.proposals.forEach(p => {
      const chosen = mappingOverrides[p.target_field] !== undefined
        ? mappingOverrides[p.target_field]
        : (p.proposed_source_field || "");
      if (chosen) mappedCount++;
      else if (p.required) unmappedReq++;
    });
  }

  let riskCount = unmappedReq;
  if (currentAssessment && currentAssessment.risks) {
    riskCount += currentAssessment.risks.length;
  }

  if (trayMapped) {
    trayMapped.textContent = totalProposals > 0 ? `${mappedCount} / ${totalProposals}` : "- / -";
  }
  if (trayRisks) {
    trayRisks.textContent = `${riskCount}`;
  }
  if (trayQuarantine) {
    if (currentResults && currentResults.validation) {
      trayQuarantine.textContent = `${currentResults.validation.quarantined_records_count || 0} Records`;
    } else {
      trayQuarantine.textContent = "0 Records";
    }
  }
  if (trayYield) {
    if (currentResults && currentResults.validation) {
      trayYield.textContent = `${currentResults.validation.contract_pass_rate}%`;
    } else if (currentAssessment) {
      trayYield.textContent = unmappedReq === 0 ? "100% (Forecast)" : "0% (Blocked)";
    } else {
      trayYield.textContent = "- %";
    }
  }

  // Step-specific pill & tray action state
  if (currentStep === 1) {
    const sourceReady = Boolean(stagedSourceFile || (document.getElementById("sample-dataset-select") && document.getElementById("sample-dataset-select").value));
    let contractReady = false;
    if (activeContractTab === "sample") {
      contractReady = Boolean(document.getElementById("sample-contract-select") && document.getElementById("sample-contract-select").value);
    } else if (activeContractTab === "upload") {
      contractReady = Boolean(stagedContractFile);
    } else if (activeContractTab === "paste") {
      const text = (document.getElementById("contract-text-area") && document.getElementById("contract-text-area").value.trim()) || "";
      if (text) {
        try { JSON.parse(text); contractReady = true; } catch (_) { contractReady = false; }
      }
    }

    const isReady = sourceReady && contractReady;
    if (dot) dot.className = isReady ? "island-dot green" : "island-dot amber";
    if (title) title.textContent = isReady ? "Preflight Ready" : "Staging Required";
    if (metric) metric.textContent = isReady ? "Source & schema staged" : "Select or drop dataset";
    if (btn) btn.disabled = !isReady;
    if (btnIcon) btnIcon.textContent = "→";
    if (btnText) btnText.textContent = "Assess";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = !isReady;
      trayPrimaryBtn.textContent = "Run Assessment →";
    }
  } else if (currentStep === 2) {
    const colCount = (currentAssessment && currentAssessment.source && currentAssessment.source.columns) ? currentAssessment.source.columns.length : 0;
    const rowCount = (currentAssessment && currentAssessment.source) ? (currentAssessment.source.total_rows || 0) : 0;
    if (dot) dot.className = "island-dot blue";
    if (title) title.textContent = "Profile Inspected";
    if (metric) metric.textContent = `${colCount} cols • ${Number(rowCount).toLocaleString()} rows`;
    if (btn) btn.disabled = false;
    if (btnIcon) btnIcon.textContent = "→";
    if (btnText) btnText.textContent = "Mapping";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = false;
      trayPrimaryBtn.textContent = "Proceed to Mapping →";
    }
  } else if (currentStep === 3) {
    const allMapped = (unmappedReq === 0);
    if (dot) dot.className = allMapped ? "island-dot green" : "island-dot amber";
    if (title) title.textContent = allMapped ? "Mappings Ready" : `${unmappedReq} Required Unmapped`;
    if (metric) metric.textContent = `${mappedCount}/${totalProposals} mapped`;
    if (btn) btn.disabled = false;
    if (btnIcon) btnIcon.textContent = "→";
    if (btnText) btnText.textContent = "Review Risks";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = false;
      trayPrimaryBtn.textContent = "Review Risks Radar →";
    }
  } else if (currentStep === 4) {
    const canApprove = (unmappedReq === 0);
    if (dot) dot.className = canApprove ? "island-dot green" : "island-dot amber";
    if (title) title.textContent = canApprove ? "Ready for Sign-Off" : `${unmappedReq} Blocker Unresolved`;
    if (metric) metric.textContent = canApprove ? "100% Required Mapped" : "Resolve required fields";
    if (btn) btn.disabled = !canApprove;
    if (btnIcon) btnIcon.textContent = canApprove ? "✓" : "✕";
    if (btnText) btnText.textContent = canApprove ? "Approve" : "Blocked";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = !canApprove;
      trayPrimaryBtn.textContent = canApprove ? "Commit & Generate Adapter →" : "Resolve Blockers First";
    }
  } else if (currentStep === 5) {
    if (dot) dot.className = "island-dot blue";
    if (title) title.textContent = "Adapter Compiled";
    if (metric) metric.textContent = "Python AST validated";
    if (btn) btn.disabled = false;
    if (btnIcon) btnIcon.textContent = "→";
    if (btnText) btnText.textContent = "Validation";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = false;
      trayPrimaryBtn.textContent = "View Validation Lab →";
    }
  } else if (currentStep === 6) {
    const hasVal = currentResults && currentResults.validation;
    const passRate = hasVal ? currentResults.validation.contract_pass_rate : 0;
    if (dot) dot.className = (hasVal && passRate >= 95) ? "island-dot green" : "island-dot amber";
    if (title) title.textContent = hasVal ? `Yield: ${passRate}%` : "Validation Lab";
    if (metric) metric.textContent = hasVal ? `${currentResults.validation.valid_records_count} pass • ${currentResults.validation.quarantined_records_count} quarn` : "Ready to inspect";
    if (btn) btn.disabled = false;
    if (btnIcon) btnIcon.textContent = "→";
    if (btnText) btnText.textContent = "Dossier";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = false;
      trayPrimaryBtn.textContent = "View Final Dossier →";
    }
  } else if (currentStep === 7) {
    if (dot) dot.className = "island-dot green";
    if (title) title.textContent = "Preflight Certified";
    if (metric) metric.textContent = "Zero-Loss Verified";
    if (btn) btn.disabled = false;
    if (btnIcon) btnIcon.textContent = "↓";
    if (btnText) btnText.textContent = "Download";
    if (trayPrimaryBtn) {
      trayPrimaryBtn.disabled = false;
      trayPrimaryBtn.textContent = "Download Preflight Package ↓";
    }
  }
}

// =============================================================================
// Helper Utilities
// =============================================================================

function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


// =============================================================================
// CRT HARDWARE TELEMETRY MONITOR (Raw WebGL + Canvas 2D)
// Authored CRT Tube with 4 Authentic Screens: Terminal, Blue Fault, Film, 8-Bit
// =============================================================================

function initCrtEngine() {
  const modal = document.getElementById("crt-monitor-modal");
  const btnToggle = document.getElementById("btn-crt-toggle");
  const btnClose = document.getElementById("btn-close-crt");
  const btnThemeSync = document.getElementById("btn-crt-theme-sync");
  const btnInject = document.getElementById("btn-crt-inject-telemetry");
  const glCanvas = document.getElementById("crt-webgl-canvas");
  const offCanvas = document.getElementById("crt-offscreen-canvas");
  const variantBtns = document.querySelectorAll(".btn-crt-var");

  const knobCurvature = document.getElementById("crt-knob-curvature");
  const knobScanlines = document.getElementById("crt-knob-scanlines");
  const knobGlow = document.getElementById("crt-knob-glow");
  const knobHum = document.getElementById("crt-knob-hum");

  if (!glCanvas || !offCanvas) return;

  const ctx2d = offCanvas.getContext("2d");
  let gl = null;
  try {
    gl = glCanvas.getContext("webgl", { antialias: false, depth: false, preserveDrawingBuffer: false }) ||
         glCanvas.getContext("experimental-webgl");
  } catch (e) {
    console.warn("WebGL not supported for CRT Monitor:", e);
    return;
  }
  if (!gl) return;

  // CRT State
  const crtState = {
    isOpen: false,
    variant: "terminal", // terminal, bluescreen, cinematic, nintendo
    startTime: performance.now(),
    lastFrameTime: performance.now(),
    animationFrameId: null,
    curvature: 0.16,
    scanlines: 0.45,
    glow: 0.50,
    hum: 0.25,
    texture: null,
    program: null,
    attribPos: -1,
    uniforms: {},
    terminalLogs: [
      "[SYSTEM] RECON HARDWARE MONITOR V2.6 ONLINE",
      "[BUS] AWAITING PRE-FLIGHT INTEGRATION TELEMETRY...",
      "[INGEST] DUAL-PORT INGEST COCKPIT ARMED (CHUNK=64KB)",
      "[DIAGNOSTIC] VENDOR_INVOICES.CSV STAGED: 5,000 ROWS",
      "[PROFILING] DISCOVERED 14 DISCRETE ATTRIBUTES",
      "[METRIC] NULLITY DRIFT: 2.0% ON 'TOTAL_AMOUNT'",
      "[METRIC] CARDINALITY: 1,890 DISTINCT NUMERIC VALUES",
      "[MAPPER] DIRECT EXACT TOKEN MATCH: ID -> INVOICE_ID",
      "[COERCION] SAFE STRING -> ISO-8601 DATETIME CONVERTER ARMED",
      "[COERCION] FLOAT TYPE CONVERSION ARMED FOR 'TOTAL_AMOUNT'",
      "[RISK_RADAR] EVALUATING STRICT CONTRACT BOUNDARIES...",
      "[GATE_ALERT] R001 FATAL BLOCKER: 'VENDOR_TAX_ID' UNMAPPED",
      "[AST_COMPILER] PYTHON AST CODEGEN PIPELINE VERIFIED",
      "[ZERO_LOSS] MATHEMATICAL EQUILIBRIUM ENFORCED:",
      "[ZERO_LOSS] N_TOTAL(5,000) = N_VALID(4,700) + N_QUARANTINE(300)",
      "[STREAM] READY FOR LIVE PRE-FLIGHT EXECUTION."
    ]
  };

  // GLSL Vertex Shader
  const vsSource = `
    attribute vec2 a_pos;
    varying vec2 v_uv;
    void main() {
      v_uv = vec2((a_pos.x + 1.0) * 0.5, 1.0 - (a_pos.y + 1.0) * 0.5);
      gl_Position = vec4(a_pos, 0.0, 1.0);
    }
  `;

  // GLSL Fragment Shader (Curvature, Scanlines, Aperture Grille, Chromatic Aberration, Bloom, Hum Bar)
  const fsSource = `
    precision highp float;
    varying vec2 v_uv;
    uniform sampler2D u_screen_texture;
    uniform vec2 u_resolution;
    uniform float u_time;
    uniform float u_curvature;
    uniform float u_scanlines;
    uniform float u_glow;
    uniform float u_hum;

    vec2 curve(vec2 uv, float b) {
      uv = (uv - 0.5) * 2.0;
      uv *= 1.0 + b * (uv.x * uv.x + uv.y * uv.y);
      return (uv / 2.0) + 0.5;
    }

    void main() {
      vec2 uv = curve(v_uv, u_curvature);

      // Outside tube boundary (dark glass bevel)
      if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        gl_FragColor = vec4(0.015, 0.015, 0.02, 1.0);
        return;
      }

      // Chromatic Aberration (fringe near corners)
      vec2 ca = vec2(0.0035 * (uv.x - 0.5), 0.0);
      float r = texture2D(u_screen_texture, uv - ca).r;
      float g = texture2D(u_screen_texture, uv).g;
      float b = texture2D(u_screen_texture, uv + ca).b;
      vec3 color = vec3(r, g, b);

      // Phosphor Halation / Bloom
      vec3 bloom = (
        texture2D(u_screen_texture, uv + vec2(0.002, 0.002)).rgb +
        texture2D(u_screen_texture, uv + vec2(-0.002, 0.002)).rgb +
        texture2D(u_screen_texture, uv + vec2(0.002, -0.002)).rgb +
        texture2D(u_screen_texture, uv + vec2(-0.002, -0.002)).rgb
      ) * 0.25;
      color += bloom * (u_glow * 0.7);

      // Horizontal Scanlines
      float scanline = sin(uv.y * u_resolution.y * 3.14159) * 0.5 + 0.5;
      color *= 1.0 - (scanline * (u_scanlines * 0.7));

      // Aperture Grille / Shadow Mask (vertical RGB stripes)
      float grille = mod(gl_FragCoord.x, 3.0);
      vec3 mask = vec3(0.88);
      if (grille < 1.0) mask = vec3(1.12, 0.88, 0.88);
      else if (grille < 2.0) mask = vec3(0.88, 1.12, 0.88);
      else mask = vec3(0.88, 0.88, 1.12);
      color = mix(color, color * mask, 0.35);

      // Rolling Hum Bar
      float bar = sin(uv.y * 6.0 - u_time * 1.8) * 0.5 + 0.5;
      color += bar * (u_hum * 0.12);

      // Micro-Flicker
      color += sin(u_time * 60.0) * 0.02;

      // Vignette
      float vig = uv.x * uv.y * (1.0 - uv.x) * (1.0 - uv.y);
      vig = clamp(pow(16.0 * vig, 0.35), 0.0, 1.0);
      color *= mix(1.0, vig, 0.45);

      gl_FragColor = vec4(color, 1.0);
    }
  `;

  // Compile WebGL Shaders
  function createShader(glCtx, type, source) {
    const s = glCtx.createShader(type);
    glCtx.shaderSource(s, source);
    glCtx.compileShader(s);
    if (!glCtx.getShaderParameter(s, glCtx.COMPILE_STATUS)) {
      console.warn("CRT Shader compile error:", glCtx.getShaderInfoLog(s));
      glCtx.deleteShader(s);
      return null;
    }
    return s;
  }

  const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
  const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
  if (!vs || !fs) return;

  const prog = gl.createProgram();
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    console.warn("CRT Program link error:", gl.getProgramInfoLog(prog));
    return;
  }
  crtState.program = prog;

  crtState.attribPos = gl.getAttribLocation(prog, "a_pos");
  crtState.uniforms = {
    screenTexture: gl.getUniformLocation(prog, "u_screen_texture"),
    resolution: gl.getUniformLocation(prog, "u_resolution"),
    time: gl.getUniformLocation(prog, "u_time"),
    curvature: gl.getUniformLocation(prog, "u_curvature"),
    scanlines: gl.getUniformLocation(prog, "u_scanlines"),
    glow: gl.getUniformLocation(prog, "u_glow"),
    hum: gl.getUniformLocation(prog, "u_hum")
  };

  // Fullscreen Quad Buffer
  const posBuf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    -1, -1,
     1, -1,
    -1,  1,
    -1,  1,
     1, -1,
     1,  1
  ]), gl.STATIC_DRAW);

  // WebGL Screen Texture
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  crtState.texture = texture;

  // Resize WebGL & Offscreen Canvas
  function resizeBacking() {
    const rect = glCanvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.min(Math.round(rect.width * dpr), 1920);
    const h = Math.min(Math.round(rect.height * dpr), 1080);

    if (glCanvas.width !== w || glCanvas.height !== h) {
      glCanvas.width = w;
      glCanvas.height = h;
      gl.viewport(0, 0, w, h);
    }

    if (offCanvas.width !== w || offCanvas.height !== h) {
      offCanvas.width = w;
      offCanvas.height = h;
    }
  }

  // ---------------------------------------------------------------------------
  // Canvas 2D Screen Renderers
  // ---------------------------------------------------------------------------

  // Screen 1: Matrix Boot Terminal
  function renderTerminalScreen(time) {
    const w = offCanvas.width;
    const h = offCanvas.height;

    ctx2d.fillStyle = "#020804";
    ctx2d.fillRect(0, 0, w, h);

    ctx2d.fillStyle = "#00ff88";
    ctx2d.font = `${Math.max(12, Math.floor(h * 0.028))}px monospace`;
    ctx2d.textBaseline = "top";

    const lineHeight = Math.floor(h * 0.046);
    const startY = Math.floor(h * 0.08);
    const startX = Math.floor(w * 0.08);

    // Terminal Title Header
    ctx2d.fillStyle = "#38ef7d";
    ctx2d.fillText(">> RECON // PRE-FLIGHT INTEGRATION TERMINAL (TTY_01)", startX, startY - lineHeight * 1.2);
    ctx2d.fillStyle = "rgba(0, 255, 136, 0.35)";
    ctx2d.fillRect(startX, startY - lineHeight * 0.4, w * 0.84, 1);

    // Log Lines
    const totalLines = crtState.terminalLogs.length;
    const visibleCount = Math.min(totalLines, Math.floor((h - startY - lineHeight * 2) / lineHeight));
    const slice = crtState.terminalLogs.slice(Math.max(0, totalLines - visibleCount));

    slice.forEach((line, i) => {
      const y = startY + i * lineHeight;
      if (line.includes("ALERT") || line.includes("FATAL") || line.includes("BLOCKER")) {
        ctx2d.fillStyle = "#ff4444";
      } else if (line.includes("ZERO_LOSS") || line.includes("VERIFIED")) {
        ctx2d.fillStyle = "#10b981";
      } else if (line.includes("METRIC") || line.includes("COERCION")) {
        ctx2d.fillStyle = "#60a5fa";
      } else {
        ctx2d.fillStyle = "#00ff88";
      }
      ctx2d.fillText(line, startX, y);
    });

    // Blinking Cursor
    if (Math.sin(time * 6.0) > 0) {
      const lastY = startY + slice.length * lineHeight;
      ctx2d.fillStyle = "#00ff88";
      ctx2d.fillText("█", startX, lastY);
    }
  }

  // Screen 2: Blue Signal Fault
  function renderBlueFaultScreen(time) {
    const w = offCanvas.width;
    const h = offCanvas.height;

    ctx2d.fillStyle = "#001299";
    ctx2d.fillRect(0, 0, w, h);

    // Random noise tearing lines
    for (let i = 0; i < 4; i++) {
      const randY = (Math.sin(time * 8.0 + i) * 0.5 + 0.5) * h;
      ctx2d.fillStyle = "rgba(255, 255, 255, 0.4)";
      ctx2d.fillRect(0, randY, w, 2);
    }

    ctx2d.fillStyle = "#ffffff";
    const fontSize = Math.max(13, Math.floor(h * 0.032));
    ctx2d.font = `bold ${fontSize}px monospace`;
    ctx2d.textBaseline = "top";

    const startX = Math.floor(w * 0.1);
    let curY = Math.floor(h * 0.12);
    const lh = Math.floor(fontSize * 1.6);

    ctx2d.fillText("*** RECON HARDWARE STOP: 0x0000007E (FATAL_CONTRACT_FAULT) ***", startX, curY);
    curY += lh * 1.8;

    ctx2d.font = `${fontSize * 0.9}px monospace`;
    ctx2d.fillText("A fatal contract boundary violation has halted integration synthesis.", startX, curY);
    curY += lh;
    ctx2d.fillText("If this is the first time you've seen this fault screen, review schema mappings.", startX, curY);
    curY += lh * 1.6;

    ctx2d.fillStyle = "#ffdd44";
    ctx2d.fillText("FATAL_CONDITION: UNMAPPED REQUIRED ATTRIBUTE DETECTED", startX, curY);
    curY += lh;
    ctx2d.fillText("OFFENDING_FIELD: vendor_tax_id (contract requires nullable: false)", startX, curY);
    curY += lh;
    ctx2d.fillText("IMPACT: Direct unhandled None will crash target production pipeline", startX, curY);
    curY += lh * 1.8;

    ctx2d.fillStyle = "#ffffff";
    ctx2d.fillText("TECHNICAL FORENSICS:", startX, curY);
    curY += lh;
    ctx2d.fillText(">>> Session ID: " + (typeof currentSessionId !== "undefined" && currentSessionId ? currentSessionId : "sess_active"), startX, curY);
    curY += lh;
    ctx2d.fillText(">>> Quarantine diversion: Active (Zero-Loss Ledger armed)", startX, curY);
    curY += lh * 1.5;
    ctx2d.fillText("Press 'U' to unmap or click 'Resolve Blockers' to proceed.", startX, curY);
  }

  // Screen 3: Monochrome Film Leader
  function renderFilmLeaderScreen(time) {
    const w = offCanvas.width;
    const h = offCanvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.32;

    ctx2d.fillStyle = "#111113";
    ctx2d.fillRect(0, 0, w, h);

    // Film Grain / Scratches
    ctx2d.strokeStyle = "rgba(255, 255, 255, 0.12)";
    ctx2d.lineWidth = 1;
    for (let s = 0; s < 5; s++) {
      const rx = (Math.sin(time * 20.0 + s * 13) * 0.5 + 0.5) * w;
      ctx2d.beginPath();
      ctx2d.moveTo(rx, 0);
      ctx2d.lineTo(rx + (Math.random() - 0.5) * 4, h);
      ctx2d.stroke();
    }

    // Outer and Inner Calibration Rings
    ctx2d.strokeStyle = "#e4e4e7";
    ctx2d.lineWidth = 3;
    ctx2d.beginPath();
    ctx2d.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx2d.stroke();

    ctx2d.beginPath();
    ctx2d.arc(cx, cy, radius * 0.65, 0, Math.PI * 2);
    ctx2d.stroke();

    // Crosshairs
    ctx2d.lineWidth = 1.5;
    ctx2d.beginPath();
    ctx2d.moveTo(cx - radius * 1.3, cy);
    ctx2d.lineTo(cx + radius * 1.3, cy);
    ctx2d.moveTo(cx, cy - radius * 1.3);
    ctx2d.lineTo(cx, cy + radius * 1.3);
    ctx2d.stroke();

    // Rotating Radar Wedge
    const angle = (time * 1.5) % (Math.PI * 2);
    ctx2d.beginPath();
    ctx2d.moveTo(cx, cy);
    ctx2d.arc(cx, cy, radius, angle, angle + 0.35);
    ctx2d.fillStyle = "rgba(255, 255, 255, 0.22)";
    ctx2d.fill();

    // Countdown Number (3, 2, 1, 0)
    const count = 3 - (Math.floor(time * 1.2) % 4);
    ctx2d.fillStyle = "#ffffff";
    ctx2d.font = `bold ${Math.floor(radius * 0.65)}px sans-serif`;
    ctx2d.textAlign = "center";
    ctx2d.textBaseline = "middle";
    ctx2d.fillText(count > 0 ? String(count) : "START", cx, cy);

    // Header & Subtext
    ctx2d.font = "bold 13px monospace";
    ctx2d.fillText("RECON FLIGHT SIMULATOR · BATCH CALIBRATION", cx, cy - radius * 1.2);
    ctx2d.font = "11px monospace";
    ctx2d.fillStyle = "#a1a1aa";
    ctx2d.fillText("5,000 SYNTHETIC RECORDS • APERTURE 35MM", cx, cy + radius * 1.25);
    ctx2d.textAlign = "left";
  }

  // Screen 4: 8-Bit Retro Console Title
  function renderNintendoScreen(time) {
    const w = offCanvas.width;
    const h = offCanvas.height;

    ctx2d.fillStyle = "#0c0824";
    ctx2d.fillRect(0, 0, w, h);

    // Pixel stars
    ctx2d.fillStyle = "#ffffff";
    for (let i = 0; i < 30; i++) {
      const sx = ((i * 137.5) % w);
      const sy = (((i * 93.7) + time * 15) % h);
      ctx2d.fillRect(sx, sy, 3, 3);
    }

    const cx = w / 2;
    ctx2d.textAlign = "center";

    // 8-bit RECON Title Banner
    ctx2d.fillStyle = "#ff0055";
    ctx2d.font = `900 ${Math.floor(h * 0.12)}px monospace`;
    ctx2d.fillText("RECON", cx + 3, h * 0.28 + 3);
    ctx2d.fillStyle = "#00ffff";
    ctx2d.fillText("RECON", cx, h * 0.28);

    ctx2d.fillStyle = "#ffff00";
    ctx2d.font = `bold ${Math.max(12, Math.floor(h * 0.035))}px monospace`;
    ctx2d.fillText("THE INTEGRATION READINESS ENGINE", cx, h * 0.38);

    // Flashing "PUSH ASSESS" prompt
    if (Math.sin(time * 5.0) > -0.2) {
      ctx2d.fillStyle = "#ffffff";
      ctx2d.font = `bold ${Math.max(13, Math.floor(h * 0.04))}px monospace`;
      ctx2d.fillText("PRESS 'ASSESS' TO RUN BATCH", cx, h * 0.55);
    }

    // 8-bit Score HUD
    const hudY = h * 0.68;
    ctx2d.font = `${Math.max(11, Math.floor(h * 0.03))}px monospace`;
    ctx2d.fillStyle = "#38ef7d";
    ctx2d.fillText("VALID RECORDS : 4,700   [94.0%]", cx, hudY);
    ctx2d.fillStyle = "#ff4444";
    ctx2d.fillText("QUARANTINED   : 0,300   [06.0%]", cx, hudY + h * 0.05);

    // Retro Copyright
    ctx2d.fillStyle = "#71717a";
    ctx2d.font = `${Math.max(10, Math.floor(h * 0.024))}px monospace`;
    ctx2d.fillText("© 2026 RECON SYSTEMS INC. · ALL RIGHTS RESERVED", cx, h * 0.88);
    ctx2d.textAlign = "left";
  }

  // Master Render Loop
  function renderFrame(now) {
    if (!crtState.isOpen) return;

    resizeBacking();
    const elapsed = (now - crtState.startTime) * 0.001;

    // 1. Draw Canvas 2D Screen Texture
    if (crtState.variant === "terminal") {
      renderTerminalScreen(elapsed);
    } else if (crtState.variant === "bluescreen") {
      renderBlueFaultScreen(elapsed);
    } else if (crtState.variant === "cinematic") {
      renderFilmLeaderScreen(elapsed);
    } else if (crtState.variant === "nintendo") {
      renderNintendoScreen(elapsed);
    }

    // 2. Upload Canvas 2D to WebGL Texture
    gl.bindTexture(gl.TEXTURE_2D, crtState.texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, offCanvas);

    // 3. Draw WebGL CRT Quad
    gl.useProgram(crtState.program);
    gl.uniform1i(crtState.uniforms.screenTexture, 0);
    gl.uniform2f(crtState.uniforms.resolution, glCanvas.width, glCanvas.height);
    gl.uniform1f(crtState.uniforms.time, elapsed);
    gl.uniform1f(crtState.uniforms.curvature, crtState.curvature);
    gl.uniform1f(crtState.uniforms.scanlines, crtState.scanlines);
    gl.uniform1f(crtState.uniforms.glow, crtState.glow);
    gl.uniform1f(crtState.uniforms.hum, crtState.hum);

    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
    gl.enableVertexAttribArray(crtState.attribPos);
    gl.vertexAttribPointer(crtState.attribPos, 2, gl.FLOAT, false, 0, 0);

    gl.drawArrays(gl.TRIANGLES, 0, 6);

    crtState.animationFrameId = requestAnimationFrame(renderFrame);
  }

  // Toggle CRT Monitor
  function openCrtMonitor() {
    crtState.isOpen = true;
    modal.classList.remove("hidden");
    variantBtns.forEach(b => b.classList.toggle("active", b.dataset.variant === crtState.variant));
    crtState.startTime = performance.now();
    cancelAnimationFrame(crtState.animationFrameId);
    crtState.animationFrameId = requestAnimationFrame(renderFrame);
  }

  function closeCrtMonitor() {
    crtState.isOpen = false;
    modal.classList.add("hidden");
    cancelAnimationFrame(crtState.animationFrameId);
  }

  function toggleCrtMonitor() {
    if (window.location.hash === '#crt') {
      openCrtMonitor();
    }
    if (crtState.isOpen) closeCrtMonitor();
    else openCrtMonitor();
  }

  // Event Listeners
  btnToggle?.addEventListener("click", toggleCrtMonitor);
  btnClose?.addEventListener("click", closeCrtMonitor);

  // Variant selector buttons
  variantBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      variantBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      crtState.variant = btn.dataset.variant;
    });
  });

  // Knobs
  knobCurvature?.addEventListener("input", (e) => {
    crtState.curvature = parseFloat(e.target.value) / 100.0;
  });
  knobScanlines?.addEventListener("input", (e) => {
    crtState.scanlines = parseFloat(e.target.value) / 100.0;
  });
  knobGlow?.addEventListener("input", (e) => {
    crtState.glow = parseFloat(e.target.value) / 100.0;
  });
  knobHum?.addEventListener("input", (e) => {
    crtState.hum = parseFloat(e.target.value) / 100.0;
  });

  // Toggle Site CRT Glow Atmosphere
  btnThemeSync?.addEventListener("click", () => {
    const isCrt = document.body.getAttribute("data-crt-theme") === "true";
    document.body.setAttribute("data-crt-theme", isCrt ? "false" : "true");
    btnThemeSync.textContent = isCrt ? "⚡ Toggle Site CRT Glow" : "✓ Site CRT Glow Active";
  });

  // Inject current Recon telemetry into CRT logs
  btnInject?.addEventListener("click", () => {
    const timeStr = new Date().toLocaleTimeString();
    crtState.terminalLogs.push(`[${timeStr}] TELEMETRY INJECTED FROM ACTIVE RECON SESSION`);
    if (window.currentAssessment) {
      crtState.terminalLogs.push(`[INGEST] DATASET ROWS: ${window.currentAssessment.source_profile?.row_count || 5000}`);
      crtState.terminalLogs.push(`[PROPOSALS] SYNTHESIZED MAPPINGS: ${window.currentAssessment.proposed_mappings?.length || 5}`);
    }
    if (window.currentValidationResult) {
      crtState.terminalLogs.push(`[LEDGER] ZERO-LOSS RATIO: ${window.currentValidationResult.contract_pass_rate}%`);
    }
    crtState.terminalLogs.push(`[SIMULATION] INTEGRATION VERIFIED WITHOUT RECON SILENT TRUNCATION.`);
  });

  // Keyboard shortcut: 'C' to toggle CRT, 'Esc' to close
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
    if (e.key.toLowerCase() === "c" && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      toggleCrtMonitor();
    } else if (e.key === "Escape" && crtState.isOpen) {
      closeCrtMonitor();
    }
  });

  // Expose on window for external telemetry hooks
  const hash = window.location.hash;
  if (hash === '#glow') {
    document.body.setAttribute('data-crt-theme', 'true');
  } else if (hash === '#crt' || hash.startsWith('#crt-')) {
    if (hash === '#crt-bluescreen') crtState.variant = 'bluescreen';
    else if (hash === '#crt-cinematic') crtState.variant = 'cinematic';
    else if (hash === '#crt-nintendo') crtState.variant = 'nintendo';
    else crtState.variant = 'terminal';
    openCrtMonitor();
  }
  window.addEventListener('hashchange', () => {
    if (window.location.hash === '#crt') openCrtMonitor();
    else if (crtState.isOpen) closeCrtMonitor();
  });

  window.ReconCRT = {
    open: openCrtMonitor,
    close: closeCrtMonitor,
    toggle: toggleCrtMonitor,
    setVariant: (v) => { crtState.variant = v; },
    log: (msg) => { crtState.terminalLogs.push(msg); }
  };
}
