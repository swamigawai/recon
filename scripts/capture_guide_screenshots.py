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
PORT = 9224
USER_DATA_DIR = os.path.expandvars(r"%TEMP%\edge_guide_cdp_" + str(int(time.time())))

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
    print("[1/4] Spawning Headless Edge...")
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
        print("[2/4] Connecting to CDP...")
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list")
        targets = json.loads(req.read().decode())
        page_target = next((t for t in targets if t.get("type") == "page"), targets[0])
        ws_url = page_target.get("webSocketDebuggerUrl")

        async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
            msg_id = 100
            await send_cdp(ws, "Page.enable", {}, msg_id); msg_id += 1
            await send_cdp(ws, "Runtime.enable", {}, msg_id); msg_id += 1
            await asyncio.sleep(1.5)

            # 1. Open Guide Modal
            print("[3/4] Clicking Guide button and capturing modal...")
            await evaluate(ws, "document.getElementById('btn-guide').click()", msg_id); msg_id += 1
            await asyncio.sleep(0.6)
            await take_screenshot(ws, "guide_modal_overview.png", msg_id); msg_id += 1

            # 2. Click Spotlight on Screen
            print("[4/4] Triggering Spotlight on Screen and capturing live UI highlight...")
            await evaluate(ws, "document.getElementById('btn-guide-spotlight-toggle').click()", msg_id); msg_id += 1
            await asyncio.sleep(0.8)
            await take_screenshot(ws, "guide_spotlight_ingest.png", msg_id); msg_id += 1

            print("[Done] All Guide verification screenshots captured successfully!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
