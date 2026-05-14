from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.cases.models.case import Case


TENANT_NAME_REPAIRS: dict[str, str] = {
    "org-5093": "演示机构 5093",
}

USER_NAME_REPAIRS: dict[tuple[str, str], str] = {
    ("test_lawfirm", "13900000001"): "陈律师",
    ("test_lawfirm", "13700000000"): "王一当事人",
    ("test_lawfirm", "13700000001"): "刘二当事人",
    ("test_lawfirm", "13900009999"): "赵三当事人",
    ("test_lawfirm", "13900008888"): "陈四当事人",
    ("test_lawfirm", "13900007777"): "孙五当事人",
    ("org-5093", "1395093"): "机构管理员 5093",
    ("org-5093", "1375093"): "演示律师 5093",
}

CASE_TITLE_REPAIRS: dict[tuple[str, str], str] = {
    ("test_lawfirm", "CASE-001"): "借款合同纠纷",
    ("test_lawfirm", "CASE-002"): "劳动报酬争议",
    ("test_lawfirm", "CASE-DEMO-001"): "离婚财产分割演示案件",
    ("test_lawfirm", "CASE-DEMO-002"): "房屋租赁纠纷演示案件",
    ("test_lawfirm", "CASE-DEMO-003"): "交通事故赔偿演示案件",
}


def _needs_repair(value: object | None) -> bool:
    if value is None:
        return True
    normalized = str(value).strip()
    return not normalized or "?" in normalized


def _tenant_by_code(db: Session, tenant_code: str) -> Tenant | None:
    return db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()


def _repair_tenants(db: Session) -> list[str]:
    updates: list[str] = []
    for tenant_code, tenant_name in TENANT_NAME_REPAIRS.items():
        tenant = _tenant_by_code(db, tenant_code)
        if tenant is None or not _needs_repair(tenant.name):
            continue
        tenant.name = tenant_name
        db.add(tenant)
        updates.append(f"tenant:{tenant_code}")
    return updates


def _repair_users(db: Session) -> list[str]:
    updates: list[str] = []
    for (tenant_code, phone), real_name in USER_NAME_REPAIRS.items():
        tenant = _tenant_by_code(db, tenant_code)
        if tenant is None:
            continue
        user = db.query(User).filter(User.tenant_id == tenant.id, User.phone == phone).first()
        if user is None or not _needs_repair(user.real_name):
            continue
        user.real_name = real_name
        db.add(user)
        updates.append(f"user:{tenant_code}:{phone}")
    return updates


def _repair_cases(db: Session) -> list[str]:
    updates: list[str] = []
    for (tenant_code, case_number), title in CASE_TITLE_REPAIRS.items():
        tenant = _tenant_by_code(db, tenant_code)
        if tenant is None:
            continue
        case = db.query(Case).filter(Case.tenant_id == tenant.id, Case.case_number == case_number).first()
        if case is None or not _needs_repair(case.title):
            continue
        case.title = title
        db.add(case)
        updates.append(f"case:{tenant_code}:{case_number}")
    return updates


def repair_demo_data(db: Session) -> list[str]:
    updates = [
        *_repair_tenants(db),
        *_repair_users(db),
        *_repair_cases(db),
    ]
    if updates:
        db.commit()
    return updates


def _print_updates(updates: Iterable[str]) -> None:
    updates = list(updates)
    if not updates:
        print("未发现需要修复的本地演示脏数据。")
        return
    print(f"已修复 {len(updates)} 条本地演示脏数据：")
    for item in updates:
        print(f"- {item}")


def main() -> None:
    with SessionLocal() as db:
        updates = repair_demo_data(db)
    _print_updates(updates)


if __name__ == "__main__":
    main()
