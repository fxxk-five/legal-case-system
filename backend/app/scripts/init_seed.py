from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
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

    print("初始化数据完成。")
    print(f"默认租户：{tenant.name} (tenant_id={tenant.id})")
    print("管理员账号：13800000000 / admin123456")
