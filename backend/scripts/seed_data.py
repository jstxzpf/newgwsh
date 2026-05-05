from sqlalchemy.orm import Session
import sys
import os

# 确保 app 模块可被导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SyncSessionLocal
from app.models.user import SystemUser, Department
from app.models.document import Document, DocumentType
from app.models.knowledge import KnowledgeBaseHierarchy
from app.models.system import SystemConfig
from app.models.enums import KBTier, DataSecurityLevel, KBTypeEnum, DocumentStatus
from app.core.security import get_password_hash
import uuid
from datetime import datetime, timedelta

def seed():
    db = SyncSessionLocal()
    try:
        # 1. 初始化科室架构
        depts_data = [
            {"name": "办公室", "code": "OFFICE"},
            {"name": "综合及核算科", "code": "COMPREHENSIVE"},
            {"name": "农业调查科", "code": "AGRICULTURE"},
            {"name": "住户调查科", "code": "HOUSEHOLD"},
            {"name": "专项调查及执法科", "code": "SPECIAL"},
        ]
        dept_map = {}
        for d in depts_data:
            dept = db.query(Department).filter(Department.dept_code == d["code"]).first()
            if not dept:
                dept = Department(dept_name=d["name"], dept_code=d["code"])
                db.add(dept)
                db.flush()
            dept_map[d["code"]] = dept.dept_id

        # 2. 初始化核心用户群
        users_data = [
            {"un": "admin", "name": "系统管理员", "pwd": "Admin123", "lvl": 99, "dept": "OFFICE"},
            {"un": "kz_nongye", "name": "王农业", "pwd": "Password123", "lvl": 5, "dept": "AGRICULTURE"},
            {"un": "ky_nongye", "name": "李小农", "pwd": "Password123", "lvl": 1, "dept": "AGRICULTURE"},
            {"un": "kz_zhuhu", "name": "张住户", "pwd": "Password123", "lvl": 5, "dept": "HOUSEHOLD"},
        ]
        user_map = {}
        for u in users_data:
            user = db.query(SystemUser).filter(SystemUser.username == u["un"]).first()
            if not user:
                user = SystemUser(
                    username=u["un"],
                    full_name=u["name"],
                    password_hash=get_password_hash(u["pwd"]),
                    role_level=u["lvl"],
                    dept_id=dept_map[u["dept"]]
                )
                db.add(user)
                db.flush()
            user_map[u["un"]] = user.user_id

        # 3. 初始化典型文种
        doc_types = [
            {"name": "通知", "code": "NOTICE", "rules": {"required_sections":["通知缘由","通知事项","执行要求","落款"]}},
            {"name": "请示", "code": "REQUEST", "rules": {"required_sections":["请示缘由","请示事项","结尾语"],"ending_template":"妥否，请批示。"}},
            {"name": "调研分析", "code": "RESEARCH", "rules": {"required_sections":["调研背景","主要发现","政策建议"]}},
            {"name": "经济信息", "code": "ECONOMIC_INFO", "rules": {"required_sections":["信息摘要","核心数据指标","趋势研判"]}},
            {"name": "通用文档", "code": "GENERAL", "rules": {"required_sections":[]}},
        ]
        type_map = {}
        for dt in doc_types:
            exists = db.query(DocumentType).filter(DocumentType.type_code == dt["code"]).first()
            if not exists:
                exists = DocumentType(type_name=dt["name"], type_code=dt["code"], layout_rules=dt["rules"])
                db.add(exists)
                db.flush()
            type_map[dt["code"]] = exists.type_id

        # 4. 初始化基础知识库 (BASE)
        base_kb_data = [
            {"name": "国家统计调查制度 (2025)", "lvl": DataSecurityLevel.GENERAL},
            {"name": "泰兴调查队公文处理规范", "lvl": DataSecurityLevel.IMPORTANT},
        ]
        for kb in base_kb_data:
            exists = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_name == kb["name"]).first()
            if not exists:
                db.add(KnowledgeBaseHierarchy(
                    kb_name=kb["name"],
                    kb_type=KBTypeEnum.FILE,
                    kb_tier=KBTier.BASE,
                    security_level=kb["lvl"],
                    owner_id=user_map["admin"],
                    parse_status="READY"
                ))

        # 5. 注入模拟实战公文 (贴合调查队实际)
        docs_data = [
            {
                "title": "关于开展2026年春季粮食产量调查的通知",
                "content": "各相关乡镇：\n根据国家统计局要求，现决定启动2026年春季粮食产量抽样调查工作...\n请农业科抓紧落实。",
                "status": DocumentStatus.DRAFTING,
                "user": "ky_nongye",
                "type": "NOTICE"
            },
            {
                "title": "泰兴市2025年度居民可支配收入情况分析",
                "content": "2025年，泰兴市居民生活水平稳步提升。据住户调查数据显示，全年人均可支配收入增长率为8%...",
                "status": DocumentStatus.SUBMITTED,
                "user": "kz_zhuhu",
                "type": "RESEARCH"
            },
            {
                "title": "关于开展2026年泰兴市规模以下工业企业抽样调查的通知",
                "content": "为准确反映我市规模以下工业运行情况，经研究，决定于4月1日起开展专项抽样调查。各科室需协同配合，确保样本框库真实准确。",
                "status": DocumentStatus.DRAFTING,
                "user": "admin",
                "type": "NOTICE"
            },
            {
                "title": "泰兴调查队2026年一季度意识形态工作总结",
                "content": "一季度，我队坚持党建引领，强化意识形态阵地建设。通过开展「书香调查」活动，提升了全队干部的理论素养...",
                "status": DocumentStatus.SUBMITTED,
                "user": "admin",
                "type": "GENERAL"
            },
            {
                "title": "关于采购移动端住户调查设备的请示",
                "content": "当前住户调查终端老化严重，为提升入户调查效率及数据安全性，申请采购20台高规格平板电脑，预算控制在6万元以内。",
                "status": DocumentStatus.DRAFTING,
                "user": "kz_zhuhu",
                "type": "REQUEST"
            },
            {
                "title": "2026年3月份泰兴市主要农产品价格变动情况简报",
                "content": "监测数据显示，3月份我市生猪价格略有回升，由于受春季气候波动影响，叶类蔬菜价格涨幅较大，粮食价格基本保持稳定。",
                "status": DocumentStatus.SUBMITTED,
                "user": "ky_nongye",
                "type": "ECONOMIC_INFO"
            }
        ]
        for d in docs_data:
            exists = db.query(Document).filter(Document.title == d["title"]).first()
            if not exists:
                db.add(Document(
                    doc_id=str(uuid.uuid4()),
                    title=d["title"],
                    content=d["content"],
                    status=d["status"],
                    doc_type_id=type_map[d["type"]],
                    creator_id=user_map[d["user"]],
                    dept_id=dept_map[users_data[[u['un'] for u in users_data].index(d['user'])]['dept']]
                ))

        # 6. 初始化系统参数
        configs = [
            {"key": "lock_ttl_seconds", "val": "180", "type": "int", "desc": "编辑锁过期时长"},
            {"key": "heartbeat_interval_seconds", "val": "90", "type": "int", "desc": "锁心跳建议频率"},
            {"key": "ollama_timeout_seconds", "val": "120", "type": "int", "desc": "AI 推理超时阈值"},
        ]
        for c in configs:
            exists = db.query(SystemConfig).filter(SystemConfig.config_key == c["key"]).first()
            if not exists:
                db.add(SystemConfig(
                    config_key=c["key"], 
                    config_value=c["val"], 
                    value_type=c["type"], 
                    description=c["desc"]
                ))

        db.commit()
        print("✅ [极致匠心] 泰兴调查队实战种子数据导入成功！")
    except Exception as e:
        db.rollback()
        print(f"❌ 种子导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed()