"""Automated production UI screenshot capture using Headless Edge / Chrome CDP.
Generates crystal-clear, high-resolution screenshots for all 7 Recon stages.
"""

import os
import sys
import time
import json
import base64
import asyncio
import subprocess
import urllib.request
import websockets

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = str(REPO_ROOT / "benchmarks" / "results" / "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

CDP_PORT = 9222
SERVER_PORT = 8000
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
        print(f"  [OK] Saved: {filename} ({len(raw_bytes):,} bytes)")
        return out_path
    else:
        print(f"  [ERR] Screenshot Failed: {filename}: {res}")
        return None


def wait_for_server(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


async def main():
    print("=" * 70)
    print("Recon UI Screenshot Engine — High-DPI Capture")
    print("=" * 70)

    # 1. Start local Recon server
    print("\n[1/7] Spawning local Recon server...")
    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "recon.cli", "serve", "--host", "127.0.0.1", "--port", str(SERVER_PORT)],
        env=server_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not wait_for_server(f"http://127.0.0.1:{SERVER_PORT}/api/health", timeout=15):
        server_proc.terminate()
        raise RuntimeError("Recon server failed to become healthy at http://127.0.0.1:8000/api/health")
    print("  Recon server online at http://127.0.0.1:8000")

    # 2. Spawn Headless Browser with remote debugging
    print(f"\n[2/7] Launching Headless Browser ({os.path.basename(EDGE_PATH)})...")
    browser_cmd = [
        EDGE_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-fre",
        "--disable-sync",
        "--inprivate",
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900",
        f"http://127.0.0.1:{SERVER_PORT}/",
    ]
    browser_proc = subprocess.Popen(browser_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.5)

    try:
        # Connect to CDP
        print("\n[3/7] Connecting to Chrome DevTools Protocol...")
        req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list")
        targets = json.loads(req.read().decode())
        page_target = next((t for t in targets if t.get("type") == "page"), targets[0])
        ws_url = page_target.get("webSocketDebuggerUrl")
        print(f"  Connected to CDP session: {ws_url}")

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            msg_id = 100

            # Enable Page and Runtime
            await send_cdp(ws, "Page.enable", {}, msg_id)
            msg_id += 1
            await send_cdp(ws, "Runtime.enable", {}, msg_id)
            msg_id += 1

            # High-DPI Display setup (scale factor 1.25 for crisp text rendering)
            await send_cdp(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 920,
                "deviceScaleFactor": 1.25,
                "mobile": False
            }, msg_id)
            msg_id += 1

            await asyncio.sleep(2.0)

            # Stage 01: Intake Cockpit
            print("\n[4/7] Capturing Stage 01 (Intake Cockpit)...")
            await take_screenshot(ws, "step01_ingest_desktop.png", msg_id)
            msg_id += 1

            # Mobile preview
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

            # Restore desktop view
            await send_cdp(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 920,
                "deviceScaleFactor": 1.25,
                "mobile": False
            }, msg_id)
            msg_id += 1
            await asyncio.sleep(0.5)

            # Load demo scenario (B2B Vendor Invoices)
            print("\n[5/7] Executing Preflight Assessment with B2B Vendor Invoicing Scenario...")
            await evaluate(ws, "loadScenario('b2b')", msg_id)
            msg_id += 1
            await asyncio.sleep(0.5)

            # Click Preflight Assessment button
            await evaluate(ws, "document.getElementById('btn-assess').click()", msg_id)
            msg_id += 1

            # Wait for assessment to complete
            for _ in range(40):
                has_assessment = await evaluate(ws, "currentAssessment !== null", msg_id)
                msg_id += 1
                if has_assessment:
                    break
                await asyncio.sleep(0.25)
            await asyncio.sleep(0.8)

            # Stage 02: Profile Matrix
            print("\n[6/7] Capturing Stages 02 through 07...")
            await evaluate(ws, "navigateToStep(2)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step02_profile_matrix.png", msg_id)
            msg_id += 1

            # Stage 03: Mapping Review Studio
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

            # Stage 04: Risk Radar & Approval Gate
            await evaluate(ws, "navigateToStep(4)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step04_risk_radar.png", msg_id)
            msg_id += 1

            # Authorize mappings and sign off
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

            # Click Approve & Generate
            await evaluate(ws, """
                const btnApprove = document.getElementById('btn-approve');
                if (btnApprove && !btnApprove.disabled) {
                    btnApprove.click();
                }
            """, msg_id)
            msg_id += 1

            # Wait until validation finishes
            for _ in range(40):
                has_results = await evaluate(ws, "currentResults !== null", msg_id)
                msg_id += 1
                if has_results:
                    break
                await asyncio.sleep(0.25)
            await asyncio.sleep(0.8)

            # Stage 05: Adapter Code Workbench
            await evaluate(ws, "navigateToStep(5)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step05_adapter_workbench.png", msg_id)
            msg_id += 1

            # Stage 06: Validation Lab & Quarantine Forensics (Apple-grade card & cell matrix)
            await evaluate(ws, "navigateToStep(6)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step06_validation_lab.png", msg_id)
            msg_id += 1

            # Stage 07: Integration Summary & Export (Direct CSV downloads, Target contract, Deploy Pack)
            await evaluate(ws, "navigateToStep(7)", msg_id)
            msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step07_readiness_dossier.png", msg_id)
            msg_id += 1

            print("\n[7/7] All production UI screenshots successfully captured!")

    finally:
        browser_proc.terminate()
        try:
            browser_proc.wait(timeout=3)
        except Exception:
            browser_proc.kill()

        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()
        print("Cleaned up server and browser processes.")


if __name__ == "__main__":
    asyncio.run(main())
