from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.db.session import SessionLocal
from app.scripts.init_seed import init_seed_data


def ensure_database_exists() -> None:
    connection = psycopg2.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname="postgres",
    )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (settings.POSTGRES_DB,),
            )
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(settings.POSTGRES_DB)
                    )
                )
    finally:
        connection.close()


def run_migrations() -> None:
    alembic_cfg = Config(str(Path(__file__).with_name("alembic.ini")))
    command.upgrade(alembic_cfg, "head")


def main() -> None:
    ensure_database_exists()
    run_migrations()

    with SessionLocal() as db:
        init_seed_data(db)


if __name__ == "__main__":
    main()
