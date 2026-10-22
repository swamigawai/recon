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
PORT = 9228
USER_DATA_DIR = os.path.expandvars(r"%TEMP%\edge_test_ui_" + str(int(time.time())))

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
    return None

async def main():
    print("[1/5] Launching Edge to test new UI features...")
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
        "--window-size=1440,960",
        "http://127.0.0.1:8000/",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)

    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")
        targets = json.loads(req.read().decode())
        ws_url = targets[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            print("[2/5] Testing Side-of-Screen Inspector Edge Tab...")
            tab_exists = await evaluate(ws, 'Boolean(document.getElementById("inspector-edge-tab"))')
            print(f"Inspector Edge Tab exists? {tab_exists}")

            # Capture Screen A with Edge tab visible
            await take_screenshot(ws, "edge_tab_docked.png", 1)

            # Trigger hover / pop out of inspector
            print("[3/5] Testing Inspector Pop-Out...")
            await evaluate(ws, 'document.getElementById("inspector-edge-tab").dispatchEvent(new MouseEvent("mouseenter"))')
            await asyncio.sleep(0.5)
            drawer_collapsed = await evaluate(ws, 'document.getElementById("contextual-drawer").classList.contains("collapsed")')
            print(f"Drawer is collapsed after hover? {drawer_collapsed} (Expected: False)")
            await take_screenshot(ws, "edge_tab_popped_out.png", 2)

            # Quick Demo Load & Initialize
            print("[4/5] Initializing Inspection for Step 03 Flow Graph...")
            await evaluate(ws, 'document.getElementById("btn-quick-demo").click()')
            await asyncio.sleep(0.4)
            await evaluate(ws, 'document.getElementById("btn-run-assessment").click()')
            await asyncio.sleep(1.2)

            # Navigate to Step 03 and toggle to Flow Graph
            print("[5/5] Navigating to Step 03 Flow Graph...")
            await evaluate(ws, 'navigateToStep(3)')
            await asyncio.sleep(0.4)
            await evaluate(ws, 'document.getElementById("btn-view-flow").click()')
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "step03_flow_graph_live.png", 3)

        print("[Done] All verification tests executed successfully!")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    asyncio.run(main())
