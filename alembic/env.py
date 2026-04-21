from logging.config import fileConfig
import asyncio
from sqlalchemy import engine_from_config, pool, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from alembic import context
import os

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

def get_sqlalchemy_url() -> str:
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        if db_url.startswith('postgresql+asyncpg'):
            return db_url.replace('postgresql+asyncpg', 'postgresql')
        return db_url
    return config.get_main_option("sqlalchemy.url")

def run_migrations_offline() -> None:
    url = get_sqlalchemy_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    url = get_sqlalchemy_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
