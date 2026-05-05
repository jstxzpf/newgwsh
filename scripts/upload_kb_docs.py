import os
import httpx
import asyncio

API_BASE = "http://localhost:8000/api/v1"
ADMIN_USER = "admin"
ADMIN_PASS = "Admin123"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "mock_docs")

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Login to get token
        print(f"Logging in as {ADMIN_USER}...")
        resp = await client.post(f"{API_BASE}/auth/login", json={
            "username": ADMIN_USER,
            "password": ADMIN_PASS
        })
        if resp.status_code != 200:
            print("Login failed!", resp.text)
            return
            
        token = resp.json().get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful.")

        # 2. Upload documents
        files_to_upload = [
            "household_income_2023.txt",
            "summer_grain_2024.txt",
            "cpi_analysis_2023.txt"
        ]

        for filename in files_to_upload:
            filepath = os.path.join(DOCS_DIR, filename)
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                continue
                
            print(f"\nUploading {filename}...")
            with open(filepath, "rb") as f:
                content = f.read()
                
            # BASE tier implies it's global. Admin can upload to BASE.
            data = {
                "kb_tier": "BASE",
                "security_level": "GENERAL"
            }
            files = {
                "file": (filename, content, "text/plain")
            }
            
            up_resp = await client.post(f"{API_BASE}/kb/upload", headers=headers, data=data, files=files)
            if up_resp.status_code == 200:
                print(f"  Success: {up_resp.json().get('data', {}).get('kb_id', up_resp.json().get('data', {}).get('node_id'))}")
            else:
                print(f"  Failed: HTTP {up_resp.status_code} - {up_resp.text}")

if __name__ == "__main__":
    asyncio.run(main())
