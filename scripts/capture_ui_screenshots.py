import os
import sys
import time
import json
import base64
import asyncio
import subprocess
import urllib.request
import websockets

SCREENSHOT_DIR = os.path.abspath(r"benchmarks\results\screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9222
USER_DATA_DIR = os.path.expandvars(r"%TEMP%\edge_recon_cdp_" + str(int(time.time())))

async def send_cdp(ws, method, params=None, msg_id=1):
    payload = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == msg_id:
            return data

async def evaluate(ws, js_expr, msg_id=1):
    res = await send_cdp(ws, "Runtime.evaluate", {"expression": js_expr, "awaitPromise": True, "returnByValue": True}, msg_id)
    return res.get("result", {}).get("result", {}).get("value")

async def take_screenshot(ws, filename, msg_id=1):
    out_path = os.path.join(SCREENSHOT_DIR, filename)
    res = await send_cdp(ws, "Page.captureScreenshot", {"format": "png"}, msg_id)
    b64_data = res.get("result", {}).get("data")
    if b64_data:
        raw_bytes = base64.b64decode(b64_data)
        with open(out_path, "wb") as f:
            f.write(raw_bytes)
        print(f"[OK Screenshot Saved] {filename} ({len(raw_bytes):,} bytes)")
        return out_path
    else:
        print(f"[ERR Screenshot Failed] {filename}: {res}")
        return None

async def main():
    print("[1/6] Spawning Headless Edge with remote debugging on port 9222...")
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
        "--window-size=1440,900",
        "http://127.0.0.1:8000/",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.5)

    try:
        # Get target WebSocket URL via /json/list
        print("[2/6] Querying CDP targets...")
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list")
        targets = json.loads(req.read().decode())
        page_target = next((t for t in targets if t.get("type") == "page"), targets[0])
        ws_url = page_target.get("webSocketDebuggerUrl")
        print(f"Connected to CDP page: {ws_url}")

        async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
            msg_id = 100

            # Enable Page and Runtime
            await send_cdp(ws, "Page.enable", {}, msg_id)
            msg_id += 1
            await send_cdp(ws, "Runtime.enable", {}, msg_id)
            msg_id += 1

            # Wait for page load
            await asyncio.sleep(2.0)

            # Step 01 Desktop
            print("[3/6] Capturing Step 01 (INGEST)...")
            await take_screenshot(ws, "step01_ingest_desktop.png", msg_id)
            msg_id += 1

            # Step 01 Mobile (390 x 844)
            await send_cdp(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 390,
                "height": 844,
                "deviceScaleFactor": 2,
                "mobile": True
            }, msg_id)
            msg_id += 1
            await asyncio.sleep(0.5)
            await take_screenshot(ws, "step01_ingest_mobile.png", msg_id)
            msg_id += 1

            # Restore Desktop metrics
            await send_cdp(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 900,
                "deviceScaleFactor": 1,
                "mobile": False
            }, msg_id)
            msg_id += 1
            await asyncio.sleep(0.5)

            # Quick load sample fixtures
            print("[4/6] Executing Quick Demo Load & Initialize Inspection...")
            for _ in range(20):
                opts = await evaluate(ws, "document.getElementById('sample-dataset-select').options.length", msg_id)
                msg_id += 1
                if opts and opts > 1:
                    break
                await asyncio.sleep(0.2)

            await evaluate(ws, "handleQuickDemoLoad()", msg_id)
            msg_id += 1
            await asyncio.sleep(0.5)

            btn_disabled = await evaluate(ws, "document.getElementById('btn-assess').disabled", msg_id)
            msg_id += 1
            print("btn-assess disabled?", btn_disabled)

            # Click Initialize Recon Inspection
            await evaluate(ws, "document.getElementById('btn-assess').click()", msg_id)
            msg_id += 1
            
            # Wait until assessment finishes
            for _ in range(40):
                has_assessment = await evaluate(ws, "currentAssessment !== null", msg_id)
                msg_id += 1
                if has_assessment:
                    break
                await asyncio.sleep(0.25)

            # Step 02: Profile Matrix
            print("[5/6] Capturing Step 02, 03, 04, 05, 06, 07...")
            await evaluate(ws, "navigateToStep(2)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step02_profile_matrix.png", msg_id)
            msg_id += 1

            # Step 03: Mapping Review Studio
            await evaluate(ws, "navigateToStep(3)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step03_mapping_studio.png", msg_id)
            msg_id += 1

            # Open drawer on first mapping row
            await evaluate(ws, """
                const firstRow = document.querySelector('#mappings-tbody tr');
                if (firstRow) firstRow.click();
            """, msg_id)
            msg_id += 1
            await asyncio.sleep(0.6)
            await take_screenshot(ws, "step03_mapping_drawer.png", msg_id)
            msg_id += 1

            # Step 04: Risk Radar & Approval Gate
            await evaluate(ws, "navigateToStep(4)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step04_risk_radar.png", msg_id)
            msg_id += 1

            # Auto-resolve unmapped required fields for demo
            await evaluate(ws, """
                document.querySelectorAll('#mappings-tbody tr.state-missing-req select').forEach(sel => {
                    if (sel.options.length > 1) {
                        sel.selectedIndex = 1;
                        sel.dispatchEvent(new Event('change'));
                    }
                });
                const chk = document.getElementById('ack-checkbox');
                if (chk) {
                    chk.checked = true;
                    chk.dispatchEvent(new Event('change'));
                }
            """, msg_id)
            msg_id += 1
            await asyncio.sleep(0.5)

            # Click Approve and Generate Adapter
            await evaluate(ws, """
                const btnApprove = document.getElementById('btn-approve');
                if (btnApprove && !btnApprove.disabled) {
                    btnApprove.click();
                }
            """, msg_id)
            msg_id += 1

            # Wait until validation results are ready
            for _ in range(40):
                has_results = await evaluate(ws, "currentResults !== null", msg_id)
                msg_id += 1
                if has_results:
                    break
                await asyncio.sleep(0.25)

            # Step 05: Adapter Code Workbench
            await evaluate(ws, "navigateToStep(5)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step05_adapter_workbench.png", msg_id)
            msg_id += 1

            # Step 06: Validation Lab & Quarantine Ledger
            await evaluate(ws, "navigateToStep(6)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step06_validation_lab.png", msg_id)
            msg_id += 1

            # Step 07: Readiness Dossier & Certified Artifacts
            await evaluate(ws, "navigateToStep(7)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step07_readiness_dossier.png", msg_id)
            msg_id += 1

            print("[6/6] All screenshots successfully generated!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
