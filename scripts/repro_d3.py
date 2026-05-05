import httpx
import asyncio

async def test_upload():
    url = "http://localhost:8000/api/v1/kb/upload"
    # Need a token. Let's try to login first.
    async with httpx.AsyncClient() as client:
        # Login
        resp = await client.post("http://localhost:8000/api/v1/auth/login", json={
            "username": "admin",
            "password": "Admin123"
        })
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload
        data = {
            "kb_tier": "PERSONAL",
            "security_level": "GENERAL",
        }
        files = {"file": ("test.txt", b"base64placeholder", "text/plain")}
        
        try:
            print(f"Uploading to {url}...")
            # Use data for Form fields and files for the file
            resp = await client.post(url, data=data, files=files, headers=headers, timeout=10)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
        except Exception as e:
            print(f"Upload failed with exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_upload())
