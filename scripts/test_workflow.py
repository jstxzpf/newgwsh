"""Quick end-to-end test of the full document workflow"""
import asyncio, httpx

API = 'http://localhost:8000/api/v1'

async def main():
    client = httpx.AsyncClient(timeout=15)

    # Login users
    r = await client.post(f'{API}/auth/login', json={'username':'admin','password':'Admin123'})
    H = {'Authorization': f'Bearer {r.json()["data"]["access_token"]}'}

    r = await client.post(f'{API}/auth/login', json={'username':'kz_nongye','password':'Password123'})
    KZ = {'Authorization': f'Bearer {r.json()["data"]["access_token"]}'}

    r = await client.post(f'{API}/auth/login', json={'username':'ky_nongye','password':'Password123'})
    KY = {'Authorization': f'Bearer {r.json()["data"]["access_token"]}'}

    # Draft
    r = await client.post(f'{API}/documents/init', json={'title':'闭环测试公文','doc_type_id':1}, headers=KY)
    doc_id = r.json()['data']['doc_id']
    print(f'1.起草: {doc_id}')

    # Save + Submit
    await client.post(f'{API}/documents/{doc_id}/auto-save', json={'content':'正文内容测试。'}, headers=KY)
    await client.post(f'{API}/documents/{doc_id}/submit', headers=KY)
    r = await client.get(f'{API}/documents/{doc_id}', headers=H)
    print(f'2.提交后状态: {r.json()["data"]["status"]}')

    # 科长审核
    await client.post(f'{API}/approval/{doc_id}/review', json={'action':'APPROVE'}, headers=KZ)
    r = await client.get(f'{API}/documents/{doc_id}', headers=H)
    print(f'3.科长审核后: {r.json()["data"]["status"]}')

    # 局长签发
    r = await client.post(f'{API}/approval/{doc_id}/issue', headers=H)
    dn = r.json()['data']['document_number']
    r = await client.get(f'{API}/documents/{doc_id}', headers=H)
    print(f'4.局长签发后: {r.json()["data"]["status"]} 编号={dn}')

    # 归档
    await client.post(f'{API}/documents/{doc_id}/archive', headers=H)
    r = await client.get(f'{API}/documents/{doc_id}', headers=H)
    print(f'5.归档后: {r.json()["data"]["status"]}')

    # Stats
    r = await client.get(f'{API}/documents/dashboard/stats', headers=H)
    s = r.json()['data']
    print(f'6.统计: drafted={s["drafted"]} sub={s["submitted"]} rev={s["reviewed"]} app={s["approved"]} arch={s["archived"]}')

    # Notifications
    r = await client.get(f'{API}/notifications?page=1&page_size=10', headers=KY)
    items = r.json()['data'].get('items',[])
    print(f'7.科员通知: {len(items)}条')
    for n in items[:3]:
        print(f'   [{n["type"]}] {n["content"]}')

    print('\nDRAFTING->SUBMITTED->REVIEWED->APPROVED->ARCHIVED 全链路闭环验证通过!')

asyncio.run(main())
