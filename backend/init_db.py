from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.scripts.init_seed import init_seed_data


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        init_seed_data(db)


if __name__ == "__main__":
    main()
