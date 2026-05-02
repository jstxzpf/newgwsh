import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_USER = "admin"
ADMIN_PASS = "Admin123!"

class APIContractTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.results = []

    def log_result(self, endpoint, method, status_code, success, message=""):
        res = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": success,
            "message": message
        }
        self.results.append(res)
        status_str = "[\u2713] PASS" if success else "[\u2717] FAIL"
        print(f"{status_str} {method} {endpoint} (Status: {status_code}) {message}")

    def test_auth(self):
        print("\n--- Testing 1. Auth & Session Management ---")
        payload = {"username": ADMIN_USER, "password": ADMIN_PASS}
        resp = self.session.post(f"{BASE_URL}/auth/login", data=payload)
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token") or data.get("data", {}).get("access_token")
            if not self.token:
                self.log_result("/auth/login", "POST", 200, False, "Token not found")
                return False
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            self.log_result("/auth/login", "POST", 200, True)
        else:
            self.log_result("/auth/login", "POST", resp.status_code, False, resp.text)
            return False

        resp = self.session.get(f"{BASE_URL}/auth/me")
        self.log_result("/auth/me", "GET", resp.status_code, resp.status_code == 200)
        return True

    def test_documents(self, doc_id):
        print("\n--- Testing 2. Core Document Workflow ---")
        resp = self.session.get(f"{BASE_URL}/documents/")
        self.log_result("/documents/", "GET", resp.status_code, resp.status_code == 200)

        resp = self.session.get(f"{BASE_URL}/documents/{doc_id}")
        self.log_result(f"/documents/{{doc_id}}", "GET", resp.status_code, resp.status_code == 200)

        payload = {"title": "API Test", "content": "Test content"}
        resp = self.session.post(f"{BASE_URL}/documents/{doc_id}/auto-save", json=payload)
        self.log_result(f"/documents/{{doc_id}}/auto-save", "POST", resp.status_code, resp.status_code == 200)

    def test_tasks(self, doc_id):
        print(f"\n--- Testing 4. Global Tasks & SSE Notifications ---")
        resp = self.session.post(f"{BASE_URL}/tasks/format", json={"doc_id": doc_id})
        task_id = None
        if resp.status_code == 200:
            task_id = resp.json().get("data", {}).get("task_id")
            self.log_result("/tasks/format", "POST", 200, True, f"Task ID: {task_id}")
        else:
            self.log_result("/tasks/format", "POST", resp.status_code, False, resp.text)

        if task_id:
            resp = self.session.get(f"{BASE_URL}/tasks/{task_id}")
            self.log_result("/tasks/{task_id}", "GET", resp.status_code, resp.status_code == 200)

        # Polish requires a lock
        acq = self.session.post(f"{BASE_URL}/locks/acquire", json={"doc_id": doc_id})
        if acq.status_code == 200:
            lock_token = acq.json().get("data", {}).get("lock_token")
            payload = {
                "doc_id": doc_id, 
                "lock_token": lock_token,
                "context_kb_ids": [], 
                "context_snapshot_version": 0, 
                "exemplar_id": None
            }
            resp = self.session.post(f"{BASE_URL}/tasks/polish", json=payload)
            self.log_result("/tasks/polish", "POST", resp.status_code, resp.status_code == 200)
            self.session.post(f"{BASE_URL}/locks/release", json={"doc_id": doc_id, "lock_token": lock_token})

    def test_locks(self, doc_id):
        print(f"\n--- Testing 5. High Precision Pessimistic Locking ---")
        resp = self.session.get(f"{BASE_URL}/locks/config")
        self.log_result("/locks/config", "GET", resp.status_code, resp.status_code == 200)

        payload = {"doc_id": doc_id}
        resp = self.session.post(f"{BASE_URL}/locks/acquire", json=payload)
        if resp.status_code == 200:
            lock_token = resp.json().get("data", {}).get("lock_token")
            self.log_result("/locks/acquire", "POST", 200, True)
            
            resp = self.session.post(f"{BASE_URL}/locks/heartbeat", json={"doc_id": doc_id, "lock_token": lock_token})
            self.log_result("/locks/heartbeat", "POST", resp.status_code, resp.status_code == 200)

            resp = self.session.post(f"{BASE_URL}/locks/release", json={"doc_id": doc_id, "lock_token": lock_token})
            self.log_result("/locks/release", "POST", resp.status_code, resp.status_code == 200)
        else:
            self.log_result("/locks/acquire", "POST", resp.status_code, False, resp.text)

    def test_sys(self):
        print("\n--- Testing 7. Advanced Infrastructure ---")
        for ep in ["status", "dashboard-stats"]:
            resp = self.session.get(f"{BASE_URL}/sys/{ep}")
            self.log_result(f"/sys/{ep}", "GET", resp.status_code, resp.status_code == 200)

    def test_kb(self):
        print("\n--- Testing 8. Knowledge Base Management ---")
        for ep in ["hierarchy", "snapshot-version"]:
            resp = self.session.get(f"{BASE_URL}/kb/{ep}")
            self.log_result(f"/kb/{ep}", "GET", resp.status_code, resp.status_code == 200)

    def test_chat(self):
        print("\n--- Testing 9. HRAG Chat ---")
        payload = {"query": "你好", "context_kb_ids": []}
        resp = self.session.post(f"{BASE_URL}/chat/stream", json=payload, stream=True)
        if resp.status_code == 200:
            self.log_result("/chat/stream", "POST", 200, True)
            resp.close()
        else:
            self.log_result("/chat/stream", "POST", resp.status_code, False, resp.text)

    def test_audit_exemplars(self):
        print("\n--- Testing 10. Audit & Exemplars ---")
        resp = self.session.get(f"{BASE_URL}/audit/")
        self.log_result("/audit/", "GET", resp.status_code, resp.status_code == 200)
        resp = self.session.get(f"{BASE_URL}/exemplars/")
        self.log_result("/exemplars/", "GET", resp.status_code, resp.status_code == 200)

    def test_notifications(self):
        print("\n--- Testing 11. Messages & Notifications ---")
        resp = self.session.get(f"{BASE_URL}/notifications/unread-count")
        self.log_result("/notifications/unread-count", "GET", resp.status_code, resp.status_code == 200)
        resp = self.session.get(f"{BASE_URL}/notifications/")
        if resp.status_code == 200:
            self.log_result("/notifications/", "GET", 200, True)
            items = resp.json().get("data", {}).get("items", [])
            if items:
                nid = items[0]["notification_id"]
                r2 = self.session.post(f"{BASE_URL}/notifications/{nid}/read")
                self.log_result(f"/notifications/{{id}}/read", "POST", r2.status_code, r2.status_code == 200)
        else:
            self.log_result("/notifications/", "GET", resp.status_code, False)

    def test_management(self):
        print("\n--- Testing 6. System Management (Users, Depts, Doc-Types) ---")
        for ep in ["users", "departments", "doc-types"]:
            resp = self.session.get(f"{BASE_URL}/{ep}/")
            self.log_result(f"/{ep}/", "GET", resp.status_code, resp.status_code == 200)

    def test_advanced_workflow(self, doc_id):
        print(f"\n--- Testing Advanced Workflow (Doc: {doc_id}) ---")
        # Snapshots
        resp = self.session.post(f"{BASE_URL}/documents/{doc_id}/snapshots")
        self.log_result("/snapshots", "POST", resp.status_code, resp.status_code == 200)
        resp = self.session.get(f"{BASE_URL}/documents/{doc_id}/snapshots")
        self.log_result("/snapshots", "GET", resp.status_code, resp.status_code == 200)

        # Apply/Discard Polish
        payload = {"final_content": "Polished content"}
        resp = self.session.post(f"{BASE_URL}/documents/{doc_id}/apply-polish", json=payload)
        self.log_result("/apply-polish", "POST", resp.status_code, resp.status_code == 200)
        resp = self.session.post(f"{BASE_URL}/documents/{doc_id}/discard-polish")
        self.log_result("/discard-polish", "POST", resp.status_code, resp.status_code == 200)

        # SSE Ticket
        resp = self.session.post(f"{BASE_URL}/sse/ticket", json={"task_id": "dummy"})
        self.log_result("/sse/ticket", "POST", resp.status_code, resp.status_code == 404)

    def test_final_verification(self, doc_id):
        print(f"\n--- Testing Final Verification (SIP/Download) ---")
        # APPROVED required
        self.session.post(f"{BASE_URL}/locks/acquire", json={"doc_id": doc_id})
        self.session.post(f"{BASE_URL}/documents/{doc_id}/submit")
        self.session.post(f"{BASE_URL}/approval/{doc_id}/review", json={"action": "APPROVED", "comments": "Final"})
        
        resp = self.session.get(f"{BASE_URL}/documents/{doc_id}/verify-sip")
        self.log_result("/verify-sip", "GET", resp.status_code, resp.status_code == 200)
        resp = self.session.get(f"{BASE_URL}/documents/{doc_id}/download")
        self.log_result("/download", "GET", resp.status_code, resp.status_code in [200, 404])

    def run_all(self):
        if not self.test_auth(): return
        res = self.session.post(f"{BASE_URL}/documents/init", json={"doc_type_id": 1, "title": "API Full Verification Doc"})
        if res.status_code != 200: return
        doc_id = res.json()["data"]["doc_id"]
        
        self.test_documents(doc_id)
        self.test_advanced_workflow(doc_id)
        self.test_tasks(doc_id)
        self.test_locks(doc_id)
        self.test_kb()
        self.test_sys()
        self.test_management()
        self.test_audit_exemplars()
        self.test_chat()
        self.test_notifications()
        self.test_final_verification(doc_id)
        
        self.session.delete(f"{BASE_URL}/documents/{doc_id}")
        print("\n--- Summary ---")
        passed = sum(1 for r in self.results if r["success"])
        print(f"Passed: {passed}/{len(self.results)}")
        if passed < len(self.results): sys.exit(1)

if __name__ == "__main__":
    APIContractTester().run_all()
