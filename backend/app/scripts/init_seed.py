from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User


def init_seed_data(db: Session) -> None:
    tenant = db.query(Tenant).filter(Tenant.tenant_code == "test_lawfirm").first()
    if tenant is None:
        tenant = Tenant(
            tenant_code="test_lawfirm",
            name="测试律所",
            type="organization",
            status=1,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    admin = db.query(User).filter(User.tenant_id == tenant.id, User.phone == "13800000000").first()
    if admin is None:
        admin = User(
            tenant_id=tenant.id,
            role="tenant_admin",
            is_tenant_admin=True,
            phone="13800000000",
            password_hash=get_password_hash("admin123456"),
            real_name="默认管理员",
            status=1,
        )
        db.add(admin)
        db.commit()
    else:
        admin.real_name = "默认管理员"
        admin.role = "tenant_admin"
        admin.is_tenant_admin = True
        admin.status = 1
        admin.password_hash = get_password_hash("admin123456")
        db.add(admin)
        db.commit()

    welcome_notification = (
        db.query(Notification)
        .filter(
            Notification.tenant_id == tenant.id,
            Notification.user_id == admin.id,
            Notification.title == "系统欢迎",
        )
        .first()
    )
    if welcome_notification is None:
        db.add(
            Notification(
                tenant_id=tenant.id,
                user_id=admin.id,
                title="系统欢迎",
                content="欢迎使用法律案件管理系统，当前环境已完成基础初始化。",
                is_read=False,
            )
        )
        db.commit()

    print("初始化数据完成。")
    print(f"默认租户：{tenant.name} (tenant_id={tenant.id})")
    print("管理员账号：13800000000 / admin123456")
