"""Automated CDP verification of interactive Flow Graph and Inspector drawer for Gate 16.

Verifies:
1. 5 Mapping Reassignment Scenarios:
   - Scenario 1: Straightforward 1-to-1 mapping
   - Scenario 2: Transformation required
   - Scenario 3: Ambiguous source selection
   - Scenario 4: Required target field with no valid source (Hard Blocker)
   - Scenario 5: Conflicting or duplicate source assignment
2. Inspector Drawer Behaviors:
   - Hover-to-open
   - 320ms delayed retract
   - Click-to-pin
   - Explicit close button (✕)
   - Keyboard shortcut 'I'
   - Keyboard shortcut 'Escape'
   - Canvas non-obstruction
"""

import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import websockets

SCREENSHOT_DIR = os.path.abspath(r"benchmarks\results\screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9228
USER_DATA_DIR = os.path.expandvars(r"%TEMP%\edge_verify_cdp_" + str(int(time.time())))


async def send_cdp(ws, method, params=None, msg_id=1):
    payload = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == msg_id:
            return data


async def evaluate(ws, js_expr, msg_id=1):
    res = await send_cdp(
        ws,
        "Runtime.evaluate",
        {"expression": js_expr, "awaitPromise": True, "returnByValue": True},
        msg_id,
    )
    return res.get("result", {}).get("result", {}).get("value")


async def take_screenshot(ws, filename, msg_id=1):
    out_path = os.path.join(SCREENSHOT_DIR, filename)
    res = await send_cdp(ws, "Page.captureScreenshot", {"format": "png"}, msg_id)
    b64_data = res.get("result", {}).get("data")
    if b64_data:
        raw_bytes = base64.b64decode(b64_data)
        with open(out_path, "wb") as f:
            f.write(raw_bytes)
        print(f"  [Screenshot] {filename} ({len(raw_bytes):,} bytes)")
        return out_path
    return None


async def run_verification():
    print("=" * 70)
    print("RECON GATE 16: INTERACTIVE FLOW GRAPH & INSPECTOR VERIFICATION")
    print("=" * 70)

    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-fre",
        "--disable-sync",
        "--inprivate",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,960",
        "http://127.0.0.1:8000/",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")
        targets = json.loads(req.read().decode())
        ws_url = targets[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            # 1. Wait for page load
            for _ in range(20):
                ready = await evaluate(ws, "document.readyState", 1)
                if ready == "complete":
                    break
                await asyncio.sleep(0.2)

            print("\n>>> Phase 1: Load Assessment & Navigate to Flow Graph")
            # Wait for sample selects to populate
            for _ in range(30):
                opts = await evaluate(ws, """
                    (() => {
                        const ds = document.getElementById("sample-dataset-select");
                        const cs = document.getElementById("sample-contract-select");
                        return (ds && ds.options.length > 1 && cs && cs.options.length > 1);
                    })()
                """, 2)
                if opts:
                    break
                await asyncio.sleep(0.2)

            await evaluate(ws, """
                (() => {
                    const ds = document.getElementById("sample-dataset-select");
                    const cs = document.getElementById("sample-contract-select");
                    if (ds && ds.options.length > 1) ds.selectedIndex = 1;
                    if (cs && cs.options.length > 1) cs.selectedIndex = 1;
                    document.getElementById("btn-assess").click();
                })()
            """, 3)

            # Wait for currentAssessment to be populated
            for _ in range(40):
                has_assessment = await evaluate(ws, "!!(currentAssessment && currentAssessment.proposals)", 4)
                if has_assessment:
                    break
                await asyncio.sleep(0.2)

            # Navigate to Step 3
            await evaluate(ws, "navigateToStep(3)", 5)
            await asyncio.sleep(0.5)

            # Switch to Flow Graph view
            await evaluate(ws, 'document.getElementById("btn-view-flow").click()', 6)
            await asyncio.sleep(0.8)

            # Check initial Flow Graph counts
            initial_stats = await evaluate(ws, """
                (() => {
                    const srcNodes = document.querySelectorAll('.flow-source-node').length;
                    const tgtNodes = document.querySelectorAll('.flow-target-node').length;
                    const svgLines = document.querySelectorAll('.flow-line').length;
                    const chips = document.querySelectorAll('.flow-chip').length;
                    return { srcNodes, tgtNodes, svgLines, chips };
                })()
            """, 6)
            print(f"  Initial Flow Graph DOM: {initial_stats}")
            assert initial_stats["srcNodes"] > 0, "Source nodes must be present"
            assert initial_stats["tgtNodes"] > 0, "Target nodes must be present"
            assert initial_stats["svgLines"] > 0, "SVG lines must be rendered"

            # -----------------------------------------------------------------
            # TEST SCENARIO 1: Straightforward 1-to-1 Mapping
            # -----------------------------------------------------------------
            print("\n>>> Phase 2.1: Test Scenario 1 — Straightforward 1:1 Mapping")
            s1 = await evaluate(ws, """
                (() => {
                    // Reassign invoice_id -> invoice_id (or first field)
                    const prop = currentAssessment.proposals[0];
                    handleMappingChange(prop.target_field, prop.target_field);
                    const ev = evaluateMappingEvidence(prop, prop.target_field);
                    
                    const tgtNode = document.querySelector(`.flow-target-node[data-field="${prop.target_field}"]`);
                    const selectEl = tgtNode.querySelector('.flow-target-select');
                    const pillText = tgtNode.querySelector('.flow-node-state-pill').textContent;
                    const chip = document.querySelector(`.flow-chip[data-target="${prop.target_field}"]`);
                    const line = document.querySelector(`.flow-line[data-target="${prop.target_field}"]`);
                    const tableRow = document.querySelector(`.mapping-row[data-target="${prop.target_field}"]`);
                    const badgeText = document.getElementById("flow-meter-type-badge").textContent;
                    const scoreText = document.getElementById("flow-meter-overall-score").textContent;
                    const nameVal = document.getElementById("fbar-name-val").textContent;
                    const typeVal = document.getElementById("fbar-type-val").textContent;
                    const patVal = document.getElementById("fbar-pattern-val").textContent;

                    return {
                        target: prop.target_field,
                        selectedValue: selectEl.value,
                        pillText,
                        chipLabel: chip ? chip.textContent : null,
                        lineStroke: line ? line.getAttribute("stroke") : null,
                        tableClass: tableRow.className,
                        badgeText,
                        scoreText,
                        nameVal,
                        typeVal,
                        patVal,
                        is100Name: ev.nameScore === 100,
                    };
                })()
            """, 7)
            print(f"  Scenario 1 Result: {s1}")
            assert "DIRECT" in s1["pillText"] or "APPROVED" in s1["pillText"]
            assert s1["chipLabel"] == "1:1 PASS"
            assert "100%" in s1["nameVal"]
            assert "100%" in s1["typeVal"]
            assert "DIRECT PASS" in s1["badgeText"] or "DIRECT" in s1["badgeText"]
            await take_screenshot(ws, "flow_graph_scenario1_direct.png", 8)

            # -----------------------------------------------------------------
            # TEST SCENARIO 2: Mapping Requiring a Transformation
            # -----------------------------------------------------------------
            print("\n>>> Phase 2.2: Test Scenario 2 — Transformation Required")
            s2 = await evaluate(ws, """
                (() => {
                    // Find a proposal requiring transformation, e.g. invoice_date or total_amount
                    let transformProp = currentAssessment.proposals.find(p => 
                        p.target_type === 'datetime' || p.target_type === 'float' || p.mapping_type === 'transformation_required'
                    );
                    if (!transformProp) transformProp = currentAssessment.proposals[1];

                    // Assign source requiring transformation
                    const srcCol = transformProp.proposed_source_field || currentAssessment.source.columns[1];
                    handleMappingChange(transformProp.target_field, srcCol);

                    const tgtNode = document.querySelector(`.flow-target-node[data-field="${transformProp.target_field}"]`);
                    const pillText = tgtNode.querySelector('.flow-node-state-pill').textContent;
                    const chip = document.querySelector(`.flow-chip[data-target="${transformProp.target_field}"]`);
                    const line = document.querySelector(`.flow-line[data-target="${transformProp.target_field}"]`);
                    const badgeText = document.getElementById("flow-meter-type-badge").textContent;
                    const scoreText = document.getElementById("flow-meter-overall-score").textContent;
                    const typeVal = document.getElementById("fbar-type-val").textContent;
                    const evidenceText = document.getElementById("flow-meter-evidence").textContent;

                    return {
                        target: transformProp.target_field,
                        source: srcCol,
                        pillText,
                        chipLabel: chip ? chip.textContent : null,
                        lineStroke: line ? line.getAttribute("stroke") : null,
                        badgeText,
                        scoreText,
                        typeVal,
                        evidenceText,
                    };
                })()
            """, 9)
            print(f"  Scenario 2 Result: {s2}")
            assert s2["chipLabel"] is not None
            assert s2["lineStroke"] == "#F59E0B", "Transformation line stroke should be amber #F59E0B"
            assert "TRANSFORM" in s2["badgeText"] or "APPROVED" in s2["badgeText"]
            await take_screenshot(ws, "flow_graph_scenario2_transform.png", 10)

            # -----------------------------------------------------------------
            # TEST SCENARIO 3: Ambiguous Source Selection
            # -----------------------------------------------------------------
            print("\n>>> Phase 2.3: Test Scenario 3 — Ambiguous Match Evaluation")
            s3 = await evaluate(ws, """
                (() => {
                    const prop = currentAssessment.proposals[0];
                    // Temporarily mock ambiguous status
                    prop.status = 'ambiguous';
                    delete mappingOverrides[prop.target_field];
                    handleMappingChange(prop.target_field, prop.proposed_source_field);
                    delete mappingOverrides[prop.target_field];
                    updateFlowGraphState(currentAssessment);
                    updateFlowConnections();
                    highlightFlowStream(prop.target_field, false);

                    const badgeText = document.getElementById("flow-meter-type-badge").textContent;
                    const scoreText = document.getElementById("flow-meter-overall-score").textContent;
                    const chip = document.querySelector(`.flow-chip[data-target="${prop.target_field}"]`);

                    // restore
                    prop.status = 'proposed';
                    return { badgeText, scoreText, chipLabel: chip ? chip.textContent : null };
                })()
            """, 11)
            print(f"  Scenario 3 Result: {s3}")
            assert "AMBIGUOUS" in s3["badgeText"]
            assert "! AMBIGUOUS" in s3["chipLabel"]

            # -----------------------------------------------------------------
            # TEST SCENARIO 4: Required Target Field with No Valid Source (Blocker)
            # -----------------------------------------------------------------
            print("\n>>> Phase 2.4: Test Scenario 4 — Missing Required Field (Blocker)")
            s4 = await evaluate(ws, """
                (() => {
                    // Find a required field
                    const reqProp = currentAssessment.proposals.find(p => p.required) || currentAssessment.proposals[0];
                    reqProp.required = true;
                    // Unmap it
                    handleMappingChange(reqProp.target_field, "");

                    const tgtNode = document.querySelector(`.flow-target-node[data-field="${reqProp.target_field}"]`);
                    const isBlockedClass = tgtNode.classList.contains("is-blocked");
                    const pillText = tgtNode.querySelector('.flow-node-state-pill').textContent;
                    const badgeText = document.getElementById("flow-meter-type-badge").textContent;
                    const scoreText = document.getElementById("flow-meter-overall-score").textContent;
                    const connText = document.getElementById("flow-meter-connection").textContent;
                    const nameVal = document.getElementById("fbar-name-val").textContent;
                    const typeVal = document.getElementById("fbar-type-val").textContent;

                    // Check Risk Radar & Approval Button
                    const radarBanner = document.getElementById("radar-status-banner").className;
                    const btnApprove = document.getElementById("btn-approve").disabled;
                    const blockersCount = document.querySelectorAll("#radar-blockers-container .blocker").length;

                    return {
                        target: reqProp.target_field,
                        isBlockedClass,
                        pillText,
                        badgeText,
                        scoreText,
                        connText,
                        nameVal,
                        typeVal,
                        radarBanner,
                        btnApproveDisabled: btnApprove,
                        blockersCount,
                    };
                })()
            """, 12)
            print(f"  Scenario 4 Result: {s4}")
            assert s4["isBlockedClass"] is True, "Target node must have .is-blocked class"
            assert "MISSING REQ" in s4["pillText"]
            assert "CRITICAL BLOCKER" in s4["badgeText"]
            assert "[UNMAPPED]" in s4["connText"]
            assert "0%" in s4["nameVal"]
            assert "0%" in s4["typeVal"]
            assert s4["btnApproveDisabled"] is True, "Approve button must be disabled when required field is unmapped"
            assert s4["blockersCount"] >= 1, "Risk Radar must register hard blocker"
            await take_screenshot(ws, "flow_graph_scenario4_blocked.png", 13)

            # -----------------------------------------------------------------
            # TEST SCENARIO 5: Conflicting or Duplicate Source Assignment
            # -----------------------------------------------------------------
            print("\n>>> Phase 2.5: Test Scenario 5 — Duplicate Source Assignment")
            s5 = await evaluate(ws, """
                (() => {
                    const p1 = currentAssessment.proposals[0];
                    const p2 = currentAssessment.proposals[1];
                    const sharedSource = currentAssessment.source.columns[0];

                    // Assign same source column to BOTH target fields
                    handleMappingChange(p1.target_field, sharedSource);
                    handleMappingChange(p2.target_field, sharedSource);

                    const node1Pill = document.querySelector(`.flow-target-node[data-field="${p1.target_field}"] .flow-node-state-pill`).textContent;
                    const node2Pill = document.querySelector(`.flow-target-node[data-field="${p2.target_field}"] .flow-node-state-pill`).textContent;
                    const chip1 = document.querySelector(`.flow-chip[data-target="${p1.target_field}"]`);
                    const chip2 = document.querySelector(`.flow-chip[data-target="${p2.target_field}"]`);
                    const badgeText = document.getElementById("flow-meter-type-badge").textContent;
                    const scoreText = document.getElementById("flow-meter-overall-score").textContent;
                    const warningCards = document.querySelectorAll("#radar-warnings-container .warning").length;

                    return {
                        sharedSource,
                        target1: p1.target_field,
                        target2: p2.target_field,
                        node1Pill,
                        node2Pill,
                        chip1Label: chip1 ? chip1.textContent : null,
                        chip2Label: chip2 ? chip2.textContent : null,
                        chip1HasDupClass: chip1 ? chip1.classList.contains("chip-duplicate") : false,
                        badgeText,
                        scoreText,
                        warningCards,
                    };
                })()
            """, 14)
            print(f"  Scenario 5 Result: {s5}")
            assert "DUPLICATE" in s5["node1Pill"]
            assert "DUPLICATE" in s5["node2Pill"]
            assert s5["chip1Label"] == "⚠ REUSED SOURCE"
            assert s5["chip2Label"] == "⚠ REUSED SOURCE"
            assert s5["chip1HasDupClass"] is True
            assert "DUPLICATE" in s5["badgeText"]
            assert s5["warningCards"] >= 1, "Risk Radar must register duplicate warning"
            await take_screenshot(ws, "flow_graph_scenario5_duplicate.png", 15)

            # -----------------------------------------------------------------
            # TEST SECTION 2: Inspector Drawer Behavior
            # -----------------------------------------------------------------
            print("\n>>> Phase 3: Verify Contextual Inspector Drawer Ergonomics")

            # Reset mapping
            await evaluate(ws, """
                (() => {
                    const p1 = currentAssessment.proposals[0];
                    const p2 = currentAssessment.proposals[1];
                    handleMappingChange(p1.target_field, p1.proposed_source_field);
                    handleMappingChange(p2.target_field, p2.proposed_source_field);
                })()
            """, 16)

            # 1. Hover-to-open
            print("  [3.1] Testing Hover-to-Open...")
            h1 = await evaluate(ws, """
                (() => {
                    const edgeTab = document.getElementById("inspector-edge-tab");
                    const drawer = document.getElementById("contextual-drawer");
                    closeInspectorDrawer(true);
                    
                    // Trigger mouseenter
                    edgeTab.dispatchEvent(new MouseEvent("mouseenter"));
                    return {
                        drawerCollapsed: drawer.classList.contains("collapsed"),
                        edgeTabActive: edgeTab.classList.contains("active")
                    };
                })()
            """, 17)
            print(f"    Hover enter: {h1}")
            assert h1["drawerCollapsed"] is False, "Drawer should expand on edge-tab hover"
            assert h1["edgeTabActive"] is True, "Edge tab should be active on hover"

            # 2. Delayed retract (320ms buffer)
            print("  [3.2] Testing Delayed Retract (320ms buffer)...")
            await evaluate(ws, """
                (() => {
                    const edgeTab = document.getElementById("inspector-edge-tab");
                    edgeTab.dispatchEvent(new MouseEvent("mouseleave"));
                })()
            """, 18)
            # Check immediately at 100ms -> should still be open!
            await asyncio.sleep(0.1)
            h2_mid = await evaluate(ws, """
                (() => {
                    const drawer = document.getElementById("contextual-drawer");
                    return { drawerCollapsed: drawer.classList.contains("collapsed") };
                })()
            """, 19)
            print(f"    Retract at 100ms: {h2_mid}")
            assert h2_mid["drawerCollapsed"] is False, "Drawer must still be open during 320ms buffer window"

            # Check after 400ms -> now collapsed!
            await asyncio.sleep(0.35)
            h2_end = await evaluate(ws, """
                (() => {
                    const drawer = document.getElementById("contextual-drawer");
                    const edgeTab = document.getElementById("inspector-edge-tab");
                    return {
                        drawerCollapsed: drawer.classList.contains("collapsed"),
                        edgeTabActive: edgeTab.classList.contains("active")
                    };
                })()
            """, 20)
            print(f"    Retract at 450ms: {h2_end}")
            assert h2_end["drawerCollapsed"] is True, "Drawer must collapse after 320ms delay"
            assert h2_end["edgeTabActive"] is False, "Edge tab must deactivate after collapse"

            # 3. Click-to-pin
            print("  [3.3] Testing Click-to-Pin...")
            p1 = await evaluate(ws, """
                (() => {
                    const edgeTab = document.getElementById("inspector-edge-tab");
                    const drawer = document.getElementById("contextual-drawer");
                    edgeTab.click();
                    return {
                        isDrawerPinned,
                        drawerCollapsed: drawer.classList.contains("collapsed"),
                        edgeTabActive: edgeTab.classList.contains("active")
                    };
                })()
            """, 21)
            print(f"    Click pin: {p1}")
            assert p1["isDrawerPinned"] is True, "Drawer should be pinned after click"
            assert p1["drawerCollapsed"] is False

            # Mouseleave when pinned must NOT retract
            await evaluate(ws, """
                (() => {
                    const drawer = document.getElementById("contextual-drawer");
                    drawer.dispatchEvent(new MouseEvent("mouseleave"));
                })()
            """, 22)
            await asyncio.sleep(0.4)
            p1_pinned = await evaluate(ws, """
                (() => {
                    const drawer = document.getElementById("contextual-drawer");
                    return { drawerCollapsed: drawer.classList.contains("collapsed"), isDrawerPinned };
                })()
            """, 23)
            print(f"    Pinned after mouseleave 400ms: {p1_pinned}")
            assert p1_pinned["drawerCollapsed"] is False, "Pinned drawer must not retract on mouseleave"

            await take_screenshot(ws, "inspector_pinned_drawer.png", 24)

            # 4. Explicit Close Button (✕)
            print("  [3.4] Testing Explicit Close Button (✕)...")
            c1 = await evaluate(ws, """
                (() => {
                    const btnClose = document.getElementById("btn-close-drawer");
                    btnClose.click();
                    const drawer = document.getElementById("contextual-drawer");
                    const edgeTab = document.getElementById("inspector-edge-tab");
                    return {
                        isDrawerPinned,
                        drawerCollapsed: drawer.classList.contains("collapsed"),
                        edgeTabActive: edgeTab.classList.contains("active")
                    };
                })()
            """, 25)
            print(f"    Close button: {c1}")
            assert c1["isDrawerPinned"] is False, "Close button must unpin drawer"
            assert c1["drawerCollapsed"] is True, "Drawer must collapse"
            assert c1["edgeTabActive"] is False

            # 5. Keyboard shortcut 'I'
            print("  [3.5] Testing Keyboard Shortcut 'I'...")
            k_i = await evaluate(ws, """
                (() => {
                    document.dispatchEvent(new KeyboardEvent("keydown", { key: "i" }));
                    const drawer = document.getElementById("contextual-drawer");
                    return {
                        drawerCollapsed: drawer.classList.contains("collapsed"),
                        isDrawerPinned
                    };
                })()
            """, 26)
            print(f"    Press 'I': {k_i}")
            assert k_i["drawerCollapsed"] is False, "'I' key must open/pin drawer"

            # 6. Keyboard shortcut 'Escape'
            print("  [3.6] Testing Keyboard Shortcut 'Escape'...")
            k_esc = await evaluate(ws, """
                (() => {
                    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
                    const drawer = document.getElementById("contextual-drawer");
                    const edgeTab = document.getElementById("inspector-edge-tab");
                    return {
                        drawerCollapsed: drawer.classList.contains("collapsed"),
                        isDrawerPinned,
                        edgeTabActive: edgeTab.classList.contains("active")
                    };
                })()
            """, 27)
            print(f"    Press 'Escape': {k_esc}")
            assert k_esc["drawerCollapsed"] is True, "'Escape' key must collapse drawer"
            assert k_esc["isDrawerPinned"] is False, "'Escape' key must unpin drawer"
            assert k_esc["edgeTabActive"] is False

            # 7. Underlying canvas interaction
            print("  [3.7] Testing Canvas Non-Obstruction...")
            canvas_test = await evaluate(ws, """
                (() => {
                    const drawer = document.getElementById("contextual-drawer");
                    const drawerStyle = window.getComputedStyle(drawer);
                    const flowView = document.getElementById("mapping-flow-view");
                    const isFlowVisible = !flowView.classList.contains("hidden");
                    return {
                        drawerTransform: drawerStyle.transform,
                        isFlowVisible,
                        drawerZIndex: drawerStyle.zIndex
                    };
                })()
            """, 28)
            print(f"    Canvas interaction check: {canvas_test}")
            assert "matrix" in canvas_test["drawerTransform"] or "translate" in canvas_test["drawerTransform"]
            assert canvas_test["isFlowVisible"] is True

        print("\n" + "=" * 70)
        print("ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
        print("=" * 70)

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(run_verification())
