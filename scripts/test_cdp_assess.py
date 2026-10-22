import asyncio
import json
import urllib.request
import websockets
import subprocess
import time

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9232

_msg_id = 1

async def main():
    global _msg_id
    cmd = [
        EDGE_PATH,
        "--headless",
        "--remote-debugging-port=" + str(PORT),
        "--user-data-dir=" + r"C:\Users\user\AppData\Local\Temp\edge_test_" + str(int(time.time())),
        "http://127.0.0.1:8000/",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")
        targets = json.loads(req.read().decode())
        ws_url = targets[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            async def eval_js(expr):
                global _msg_id
                _msg_id += 1
                curr_id = _msg_id
                await ws.send(json.dumps({"id": curr_id, "method": "Runtime.evaluate", "params": {"expression": expr, "awaitPromise": True, "returnByValue": True}}))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == curr_id:
                        return data.get("result", {}).get("result", {}).get("value")

            # wait for page load
            for _ in range(20):
                ready = await eval_js("document.readyState")
                if ready == "complete":
                    break
                await asyncio.sleep(0.2)

            for _ in range(20):
                cnt = await eval_js("document.getElementById('sample-dataset-select').options.length")
                if cnt and cnt > 1:
                    break
                await asyncio.sleep(0.2)

            print("ds options count:", cnt)

            res = await eval_js("""
                (async () => {
                    const ds = document.getElementById("sample-dataset-select");
                    const cs = document.getElementById("sample-contract-select");
                    ds.value = "b2b_vendor_invoices_raw";
                    cs.value = "target_contract_b2b_vendor_invoice";
                    await handleAssessIntegration();
                    return {
                        hasAssessment: Boolean(window.currentAssessment),
                        proposalsCount: window.currentAssessment ? window.currentAssessment.proposals.length : 0,
                        currentStep: window.currentStep,
                        error: document.getElementById("global-error-msg").textContent
                    };
                })()
            """)
            print("Assess result:", res)

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    asyncio.run(main())
