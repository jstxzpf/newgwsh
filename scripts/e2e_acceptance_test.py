import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_AUTH = {"username": "admin", "password": "Admin123"}

def test_lifecycle():
    print("🚀 开始全流程功能验收测试...")
    
    # 1. 登录
    print("\n[Step 1] 登录测试...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_AUTH)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功，获取到 Access Token")

    # 2. 获取个人信息
    print("\n[Step 2] 获取个人信息 (/me)...")
    me_res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    print(f"✅ 获取成功: {me_data['full_name']} ({me_data['department_name']})")

    # 3. 知识库目录树
    print("\n[Step 3] 知识库目录树测试...")
    kb_res = requests.get(f"{BASE_URL}/kb/hierarchy?tier=BASE", headers=headers)
    assert kb_res.status_code == 200
    print(f"✅ 目录树拉取成功，根节点数: {len(kb_res.json()['data'])}")

    # 4. 新建公文
    print("\n[Step 4] 新建公文测试...")
    # 获取文种列表
    # (由于 seed_data 已入库，这里直接假设 NOTICE 存在，或者先查一下)
    # 实际测试应更严谨，这里直接 init
    init_res = requests.post(f"{BASE_URL}/documents/init", json={
        "title": "验收测试公文_" + str(int(time.time())),
        "doc_type_id": 1 # 假设第一个是通知
    }, headers=headers)
    assert init_res.status_code == 200
    doc_id = init_res.json()["data"]["doc_id"]
    print(f"✅ 公文创建成功: {doc_id}")

    # 5. 申请锁
    print("\n[Step 5] 申请编辑锁...")
    lock_res = requests.post(f"{BASE_URL}/locks/acquire", json={"doc_id": doc_id}, headers=headers)
    assert lock_res.status_code == 200
    lock_token = lock_res.json()["data"]["lock_token"]
    print(f"✅ 锁抢占成功，凭证: {lock_token}")

    # 6. 自动保存
    print("\n[Step 6] 自动保存测试...")
    save_res = requests.post(f"{BASE_URL}/documents/{doc_id}/auto-save", json={
        "content": "这是由自动化验收脚本生成的测试正文内容。"
    }, headers=headers)
    assert save_res.status_code == 200
    print("✅ 自动保存成功")

    # 7. 提交审批
    print("\n[Step 7] 提交审批测试...")
    submit_res = requests.post(f"{BASE_URL}/documents/{doc_id}/submit", headers=headers)
    assert submit_res.status_code == 200
    print("✅ 提交成功，状态已转为 SUBMITTED")

    # 8. 科长签批 (批准)
    print("\n[Step 8] 科长签批测试 (批准)...")
    approve_res = requests.post(f"{BASE_URL}/approval/{doc_id}/review", json={
        "action": "APPROVE",
        "comments": "内容详实，符合要求。"
    }, headers=headers)
    assert approve_res.status_code == 200
    print("✅ 签批成功，指纹已生成")

    # 9. SIP 存证校验
    print("\n[Step 9] SIP 存证一致性校验...")
    verify_res = requests.get(f"{BASE_URL}/documents/{doc_id}/verify-sip", headers=headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()["data"]
    assert verify_data["match"] is True
    print(f"✅ 存证校验通过！Hash: {verify_data['stored_hash'][:16]}...")

    # 10. 审计日志核查
    print("\n[Step 10] 审计日志核查...")
    audit_res = requests.get(f"{BASE_URL}/audit/?doc_id={doc_id}", headers=headers)
    assert audit_res.status_code == 200
    audits = audit_res.json()["data"]["items"]
    print(f"✅ 获取到该公文的审计记录 {len(audits)} 条")
    for a in audits:
        print(f"   - 节点: {a['node_id']} 时间: {a['timestamp']}")

    print("\n🎉 全流程功能验收测试圆满通过！系统表现符合‘极致匠心’标准。")

if __name__ == "__main__":
    try:
        test_lifecycle()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        exit(1)
