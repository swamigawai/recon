import asyncio
import json
import urllib.request
import websockets

async def check():
    req = urllib.request.urlopen("http://127.0.0.1:8000/api/sample-datasets")
    print("datasets:", req.read().decode())
    req2 = urllib.request.urlopen("http://127.0.0.1:8000/api/sample-contracts")
    print("contracts:", req2.read().decode()[:300])

if __name__ == "__main__":
    asyncio.run(check())
