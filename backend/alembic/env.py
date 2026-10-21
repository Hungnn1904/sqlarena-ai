from alembic import context
from sqlalchemy import create_engine

from app.config import get_settings

url = get_settings().database_url


def run_migrations_online() -> None:
    engine = create_engine(url, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None, version_table_schema="public")
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
