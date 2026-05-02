import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, async_engine
from app.models.base import Base
from app.models.org import Department, SystemUser
from app.models.config import DocumentType, SystemConfig
from app.core.security import get_password_hash
from sqlalchemy import select

async def seed_data():
    async with AsyncSessionLocal() as db:
        # 1. 创建基础科室
        stmt = select(Department).where(Department.dept_code == "ADMIN")
        existing_dept = await db.execute(stmt)
        if not existing_dept.scalar_one_or_none():
            admin_dept = Department(
                dept_name="办公室(管理员)",
                dept_code="ADMIN",
                is_active=True
            )
            db.add(admin_dept)
            await db.flush()
            
            # 2. 创建初始管理员
            admin_user = SystemUser(
                username="admin",
                full_name="系统管理员",
                password_hash=get_password_hash("Admin123!"),
                dept_id=admin_dept.dept_id,
                role_level=99,
                is_active=True
            )
            db.add(admin_user)
            print("Admin user created: admin / Admin123!")

        # 3. 初始化公文文种 (GB/T 9704-2023)
        doc_types = [
            ("NOTICE", "通知", {"required_sections": ["缘由", "事项", "落款"]}),
            ("REQUEST", "请示", {"required_sections": ["缘由", "事项", "结尾请批语"], "ending_template": "妥否，请批示。"}),
            ("REPORT", "报告", {"required_sections": ["缘由", "事项", "结尾报告语"], "ending_template": "特此报告。"}),
            ("RESEARCH", "调研分析", {"required_sections": ["调研背景", "调研方法", "主要发现", "分析结论", "政策建议"]}),
            ("GENERAL", "通用文档", {"required_sections": []}),
        ]
        
        for code, name, rules in doc_types:
            stmt = select(DocumentType).where(DocumentType.type_code == code)
            res = await db.execute(stmt)
            if not res.scalar_one_or_none():
                dt = DocumentType(type_code=code, type_name=name, layout_rules=rules)
                db.add(dt)
        
        # 4. 初始化系统参数 (对照实体设计 12)
        configs = [
            ("lock_ttl_seconds", "180", "int", "编辑锁超时时长（秒）"),
            ("heartbeat_interval_seconds", "90", "int", "锁心跳间隔（秒）"),
            ("ollama_timeout_seconds", "120", "int", "Ollama HTTP 请求超时（秒）"),
            ("ai_rate_limit_per_minute", "5", "int", "AI 接口单用户限流"),
            ("auto_save_interval_seconds", "60", "int", "自动保存间隔"),
            ("task_max_retries", "3", "int", "异步任务最大重试次数"),
            ("gin_cleanup_batch_size", "5000", "int", "GIN 索引维护每批处理行数")
        ]
        
        for key, val, vtype, desc in configs:
            stmt = select(SystemConfig).where(SystemConfig.config_key == key)
            res = await db.execute(stmt)
            if not res.scalar_one_or_none():
                sc = SystemConfig(config_key=key, config_value=val, value_type=vtype, description=desc)
                db.add(sc)

        await db.commit()
        print("Seeding completed successfully.")

async def main():
    # 创建所有表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await seed_data()

if __name__ == "__main__":
    asyncio.run(main())
