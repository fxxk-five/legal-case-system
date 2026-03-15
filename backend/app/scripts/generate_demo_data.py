from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.case import Case
from app.models.file import File
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User


def _get_or_create_user(
    db: Session,
    *,
    tenant_id: int,
    phone: str,
    real_name: str,
    role: str,
    password: str,
    is_tenant_admin: bool = False,
) -> User:
    user = db.query(User).filter(User.tenant_id == tenant_id, User.phone == phone).first()
    if user is None:
        user = User(
            tenant_id=tenant_id,
            phone=phone,
            real_name=real_name,
            role=role,
            is_tenant_admin=is_tenant_admin,
            password_hash=get_password_hash(password),
            status=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    user.real_name = real_name
    user.role = role
    user.is_tenant_admin = is_tenant_admin
    user.status = 1
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_or_create_case(
    db: Session,
    *,
    tenant_id: int,
    case_number: str,
    title: str,
    status: str,
    client_id: int,
    assigned_lawyer_id: int,
    deadline: datetime | None,
) -> Case:
    case = (
        db.query(Case)
        .filter(Case.tenant_id == tenant_id, Case.case_number == case_number)
        .first()
    )
    if case is None:
        case = Case(
            tenant_id=tenant_id,
            case_number=case_number,
            title=title,
            status=status,
            client_id=client_id,
            assigned_lawyer_id=assigned_lawyer_id,
            deadline=deadline,
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        return case

    case.title = title
    case.status = status
    case.client_id = client_id
    case.assigned_lawyer_id = assigned_lawyer_id
    case.deadline = deadline
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _ensure_file_record(
    db: Session,
    *,
    tenant_id: int,
    case_id: int,
    uploader_id: int,
    file_name: str,
    file_type: str,
    content: str,
) -> File:
    existing = (
        db.query(File)
        .filter(File.tenant_id == tenant_id, File.case_id == case_id, File.file_name == file_name)
        .first()
    )
    if existing is not None:
        return existing

    storage_root = Path(settings.LOCAL_STORAGE_DIR)
    target_dir = storage_root / f"tenant_{tenant_id}" / f"case_{case_id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_name
    target_path.write_text(content, encoding="utf-8")

    file_record = File(
        tenant_id=tenant_id,
        case_id=case_id,
        uploader_id=uploader_id,
        file_name=file_name,
        file_url=str(target_path.as_posix()),
        file_type=file_type,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


def _ensure_notification(db: Session, *, user_id: int, title: str, content: str) -> None:
    exists = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.title == title)
        .first()
    )
    if exists is not None:
        return

    db.add(Notification(user_id=user_id, title=title, content=content, is_read=False))
    db.commit()


def generate_demo_data(db: Session) -> None:
    tenant = db.query(Tenant).filter(Tenant.tenant_code == "test_lawfirm").first()
    if tenant is None:
        raise RuntimeError("默认租户不存在，请先执行初始化脚本。")

    admin = _get_or_create_user(
        db,
        tenant_id=tenant.id,
        phone="13800000000",
        real_name="默认管理员",
        role="tenant_admin",
        password="admin123456",
        is_tenant_admin=True,
    )
    lawyer = _get_or_create_user(
        db,
        tenant_id=tenant.id,
        phone="13900000011",
        real_name="演示律师",
        role="lawyer",
        password="lawyer123456",
    )
    client_a = _get_or_create_user(
        db,
        tenant_id=tenant.id,
        phone="13900000021",
        real_name="张三当事人",
        role="client",
        password="client123456",
    )
    client_b = _get_or_create_user(
        db,
        tenant_id=tenant.id,
        phone="13900000022",
        real_name="李四当事人",
        role="client",
        password="client123456",
    )

    now = datetime.now(timezone.utc)
    case_1 = _get_or_create_case(
        db,
        tenant_id=tenant.id,
        case_number="CASE-DEMO-1001",
        title="劳动争议仲裁演示案件",
        status="processing",
        client_id=client_a.id,
        assigned_lawyer_id=lawyer.id,
        deadline=now + timedelta(days=7),
    )
    case_2 = _get_or_create_case(
        db,
        tenant_id=tenant.id,
        case_number="CASE-DEMO-1002",
        title="合同纠纷诉讼演示案件",
        status="new",
        client_id=client_b.id,
        assigned_lawyer_id=lawyer.id,
        deadline=now + timedelta(days=15),
    )
    case_3 = _get_or_create_case(
        db,
        tenant_id=tenant.id,
        case_number="CASE-DEMO-1003",
        title="民间借贷调解演示案件",
        status="done",
        client_id=client_a.id,
        assigned_lawyer_id=admin.id,
        deadline=now - timedelta(days=3),
    )

    _ensure_file_record(
        db,
        tenant_id=tenant.id,
        case_id=case_1.id,
        uploader_id=lawyer.id,
        file_name="劳动争议起诉材料.txt",
        file_type="text/plain",
        content="这是劳动争议案件的演示材料，用于本地预览和下载测试。",
    )
    _ensure_file_record(
        db,
        tenant_id=tenant.id,
        case_id=case_2.id,
        uploader_id=client_b.id,
        file_name="合同证据清单.txt",
        file_type="text/plain",
        content="这是合同纠纷案件的当事人证据清单，用于文件上传演示。",
    )
    _ensure_file_record(
        db,
        tenant_id=tenant.id,
        case_id=case_3.id,
        uploader_id=admin.id,
        file_name="调解结案说明.txt",
        file_type="text/plain",
        content="这是已结案案件的调解说明，用于时间线和文件列表演示。",
    )

    _ensure_notification(
        db,
        user_id=admin.id,
        title="演示环境已就绪",
        content="系统已自动生成演示案件、通知和文件，可直接开始演示。",
    )
    _ensure_notification(
        db,
        user_id=lawyer.id,
        title="请跟进劳动争议案件",
        content="演示案件 CASE-DEMO-1001 将在 7 天后到期，请及时处理。",
    )
    _ensure_notification(
        db,
        user_id=lawyer.id,
        title="合同纠纷材料已上传",
        content="当事人已上传 CASE-DEMO-1002 的证据材料，请及时查看。",
    )

    print("演示数据初始化完成。")
    print("演示律师账号：13900000011 / lawyer123456")
    print("演示当事人账号：13900000021 / client123456")
    print("演示案件：CASE-DEMO-1001、CASE-DEMO-1002、CASE-DEMO-1003")


def main() -> None:
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        generate_demo_data(db)


if __name__ == "__main__":
    main()
